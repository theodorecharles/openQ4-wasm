#!/usr/bin/env python3
"""Regression checks for relative filesystem mutation qpath safety."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INVALID_WINDOWS_CHARACTERS = set('<>:"\\|?*')
WINDOWS_DEVICE_NAMES = {"con", "prn", "aux", "nul"}
WINDOWS_DEVICE_NAMES.update(f"com{digit}" for digit in "123456789¹²³")
WINDOWS_DEVICE_NAMES.update(f"lpt{digit}" for digit in "123456789¹²³")


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(haystack: str, needle: str, context: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"Missing {needle!r} in {context}")


def reject(haystack: str, needle: str, context: str) -> None:
    if needle in haystack:
        raise AssertionError(f"Unexpected {needle!r} in {context}")


def require_order(haystack: str, first: str, second: str, context: str) -> None:
    first_index = haystack.find(first)
    second_index = haystack.find(second)
    if first_index == -1 or second_index == -1:
        raise AssertionError(f"Missing ordered symbols {first!r} and/or {second!r} in {context}")
    if first_index >= second_index:
        raise AssertionError(f"Expected {first!r} before {second!r} in {context}")


def function_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start == -1:
        raise AssertionError(f"Missing function signature {signature!r}")

    depth = 0
    for index in range(start, len(source)):
        character = source[index]
        if character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]

    raise AssertionError(f"Could not find end of function {signature!r}")


def is_safe_relative_write_path_model(relative_path: str | None) -> bool:
    if not relative_path or relative_path.startswith(("/", "\\")):
        return False
    if any(ord(character) < 32 or character in INVALID_WINDOWS_CHARACTERS for character in relative_path):
        return False

    for segment in relative_path.split("/"):
        if not segment or segment in (".", "..") or segment.startswith(" ") or segment.endswith((".", " ")):
            return False
        stem = segment.split(".", 1)[0].lower()
        if stem in WINDOWS_DEVICE_NAMES:
            return False
    return True


def validate_behavior_model() -> None:
    accepted = (
        "openq4.cfg",
        "savegames/Quicksave0.save",
        "screenshots/shot00001.tga",
        "generated/rendermodels/maps/game/test.bmd5mesh",
        "logs/openq4.log",
        ".cache/generated.bin",
        "savegames/Player 1.save",
        "version..cfg",
        "devices/com10.cfg",
        "devices/lpt0.cfg",
        "devices/console.txt",
        "devices/auxiliary.txt",
    )
    rejected = (
        None,
        "",
        "/outside.cfg",
        "\\outside.cfg",
        "C:/outside.cfg",
        "C:outside.cfg",
        "../outside.cfg",
        "folder/../outside.cfg",
        "./inside.cfg",
        "folder/./inside.cfg",
        "folder//inside.cfg",
        "folder/",
        "folder\\inside.cfg",
        "folder\ninside.cfg",
        "folder\tinside.cfg",
        "folder/<inside>.cfg",
        'folder/"inside".cfg',
        "folder/inside?.cfg",
        "folder/inside*.cfg",
        "folder/inside|stream.cfg",
        "folder./inside.cfg",
        " folder/inside.cfg",
        "folder/ inside.cfg",
        "folder /inside.cfg",
        "inside.cfg.",
        "inside.cfg ",
        "con",
        "CON.txt",
        "folder/prn.cfg",
        "folder/AUX.data",
        "folder/nul.tar.gz",
        "folder/com1.cfg",
        "folder/COM9",
        "folder/lpt1.cfg",
        "folder/LPT9",
        "folder/com¹.cfg",
        "folder/COM².cfg",
        "folder/lpt³.cfg",
    )

    for path in accepted:
        if not is_safe_relative_write_path_model(path):
            raise AssertionError(f"Expected accepted relative mutation qpath: {path!r}")
    for path in rejected:
        if is_safe_relative_write_path_model(path):
            raise AssertionError(f"Expected rejected relative mutation qpath: {path!r}")


def validate_source_contract() -> None:
    source = read("src/framework/FileSystem.cpp")
    header = read("src/framework/FileSystem.h")

    device_helper = function_body(source, "static bool FS_IsWindowsDeviceQPathSegment(")
    validator = function_body(source, "static bool FS_ValidateRelativeWritePath(")
    open_write = function_body(source, "idFile *idFileSystemLocal::OpenFileWrite(")
    open_append = function_body(source, "idFile *idFileSystemLocal::OpenFileAppend(")
    remove_file = function_body(source, "void idFileSystemLocal::RemoveFile(")
    remove_file_checked = function_body(source, "bool idFileSystemLocal::RemoveFileChecked(")
    promote_file = function_body(source, "bool idFileSystemLocal::PromoteFile(")
    write_file = function_body(source, "int idFileSystemLocal::WriteFile(")
    open_by_mode = function_body(source, "idFile *idFileSystemLocal::OpenFileByMode(")
    explicit_write = function_body(source, "idFile *idFileSystemLocal::OpenExplicitFileWrite(")
    explicit_remove = function_body(source, "int idFileSystemLocal::RemoveExplicitFile(")
    create_os_path = function_body(source, "void idFileSystemLocal::CreateOSPath(")

    require(validator, "relativePath == NULL || relativePath[ 0 ] == '\\0'", "empty mutation qpath rejection")
    require(validator, "relativePath[ 0 ] == '/' || relativePath[ 0 ] == '\\\\'", "rooted mutation qpath rejection")
    require(validator, "c == '\\\\' || c == ':'", "OS separator and volume marker rejection")
    require(validator, "c < 32", "control-character rejection")
    for character in ("<", ">", '"', "|", "?", "*"):
        require(validator, f"c == '{character}'", "Windows punctuation rejection")
    require(validator, "segmentLength == 0", "empty qpath segment rejection")
    require(validator, "segmentStart[ 0 ] == '.'", "dot qpath segment rejection")
    require(validator, "segmentStart[ 1 ] == '.'", "parent qpath segment rejection")
    require(validator, "segmentStart[ 0 ] == ' '", "leading-space rejection")
    require(validator, "segmentStart[ segmentLength - 1 ] == '.'", "trailing-dot rejection")
    require(validator, "segmentStart[ segmentLength - 1 ] == ' '", "trailing-space rejection")
    require(validator, "FS_IsWindowsDeviceQPathSegment( segmentStart, segmentLength )", "device-name rejection")

    for device_name in ("con", "prn", "aux", "nul", "com", "lpt"):
        require(device_helper, f'"{device_name}"', "Windows device-name rejection")
    require(device_helper, "digit >= '1' && digit <= '9'", "numbered Windows device-name rejection")
    require(device_helper, "digit == 0xB9", "superscript Windows device-name rejection")
    require(device_helper, "digit == 0xC2", "UTF-8 superscript Windows device-name rejection")

    for body, context, first_mutation in (
        (write_file, "whole-file write API", "idFileSystemLocal::OpenFileWrite("),
        (open_write, "relative write API", "BuildOSPath("),
        (open_append, "relative append API", "BuildOSPath("),
        (remove_file, "relative remove API", "BuildOSPath("),
        (remove_file_checked, "checked relative remove API", "BuildOSPath("),
    ):
        require(body, "FS_ValidateRelativeWritePath( relativePath, &invalidReason )", context)
        require(body, "refusing unsafe relative path", context)
        require_order(body, "FS_ValidateRelativeWritePath(", first_mutation, context)

    require(write_file, "idFileSystemLocal::OpenFileWrite( relativePath, basePath )", "whole-file write funnel")
    require(open_by_mode, "OpenFileWrite( relativePath )", "mode write funnel")
    require(open_by_mode, "OpenFileAppend( relativePath, true )", "mode append funnel")

    require(remove_file_checked, "removalError == ENOENT",
            "checked cleanup treats an absent file as complete")
    require(remove_file_checked, "BuildOSPath( root, gameFolder, relativePath )",
            "checked cleanup resolves exactly one selected root")
    reject(remove_file_checked, "fs_cdpath", "checked cleanup does not walk overlay roots")

    for token in ("SDL_RenamePath", "MoveFileExA", "rename("):
        require(promote_file, token, "cross-platform atomic promotion")
    for token in ("CopyFile", "WriteFile(", "OpenFileWrite("):
        reject(promote_file, token, "atomic promotion has no copy fallback")

    for body, context in (
        (explicit_write, "explicit OS-path write API"),
        (explicit_remove, "explicit OS-path remove API"),
        (create_os_path, "explicit OS-path directory API"),
    ):
        reject(body, "FS_ValidateRelativeWritePath", context)

    require(header, "Relative mutation paths must be non-empty portable qpaths", "filesystem API contract")
    require(header, "Use the Explicit/OSPath APIs", "explicit OS-path API contract")
    require(header, "virtual bool\t\t\tRemoveFileChecked(", "checked relative cleanup API")
    require(header, "Returns true when the file was removed or was already absent.",
            "checked cleanup missing-file semantics")


def validate_generated_loadscreen_publication() -> None:
    session = read("src/framework/Session.cpp")
    image_files = read("src/imagetools/Image_files.cpp")
    image_header = read("src/renderer/Image.h")
    image_tools_header = read("src/imagetools/ImageTools.h")
    prepare = function_body(
        session,
        "static bool Session_PrepareExpandedLoadingBackground(",
    )
    secure_staging_failure = function_body(
        prepare,
        "if ( !Sys_GetSecureRandomBytes( stagingNonce, sizeof( stagingNonce ) ) )",
    )
    writer = function_body(image_files, "bool R_WriteTGA(")

    require(writer, "return fileSystem->WriteFile( filename, buffer, bufferSize, basePath ) == bufferSize;",
            "TGA writer reports short writes")
    require(image_header, "bool\tR_WriteTGA(", "renderer TGA writer result contract")
    require(image_tools_header, "bool\tR_WriteTGA(", "imagetools TGA writer result contract")
    require(prepare, "static uint32 stagingSequence = 0;",
            "generated loadscreen per-process staging sequence")
    require(prepare, "uint64 stagingNonce[2] = { 0, 0 };",
            "generated loadscreen 128-bit staging nonce")
    require(prepare, "Sys_GetSecureRandomBytes( stagingNonce, sizeof( stagingNonce ) )",
            "generated loadscreen cross-process CSPRNG token")
    require(secure_staging_failure, "Could not create a secure expanded-loadscreen staging path",
            "generated loadscreen no-CSPRNG source fallback")
    require(secure_staging_failure, "return false;",
            "generated loadscreen no-CSPRNG early return")
    require(prepare, 'const idStr stagingPath = va( "%s.%016llx%016llx.%u.partial"',
            "generated loadscreen unique staging path")
    require(prepare, "R_WriteTGA( stagingPath.c_str()", "generated loadscreen staged write")
    require(prepare, "fileSystem->PromoteFile( stagingPath.c_str(), generatedPath.c_str()",
            "generated loadscreen atomic publication")
    require(prepare, "fileSystem->RemoveFileChecked( stagingPath.c_str()",
            "generated loadscreen failed-stage cleanup")
    require(prepare, "return published;", "generated loadscreen failure falls back to source")
    require_order(prepare, "R_WriteTGA( stagingPath.c_str()", "fileSystem->PromoteFile(",
                  "generated loadscreen write-before-publish order")
    require_order(prepare, "Sys_GetSecureRandomBytes( stagingNonce, sizeof( stagingNonce ) )",
                  'const idStr stagingPath = va( "%s.%016llx%016llx.%u.partial"',
                  "generated loadscreen secure-token-before-path order")
    require_order(prepare, "Sys_GetSecureRandomBytes( stagingNonce, sizeof( stagingNonce ) )",
                  "R_WriteTGA( stagingPath.c_str()",
                  "generated loadscreen secure-token-before-write order")
    reject(prepare, "R_WriteTGA( generatedPath.c_str()",
           "generated loadscreen must never truncate the live file in place")
    reject(prepare, "Sys_GetClockTicks()",
           "generated loadscreen staging token must not use a cross-process clock fallback")


def main() -> int:
    validate_behavior_model()
    validate_source_contract()
    validate_generated_loadscreen_publication()
    print("filesystem relative mutation qpath safety checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
