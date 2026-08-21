#!/usr/bin/env python3
"""Regression checks for openQ4 pure-pack handling."""

from __future__ import annotations

import importlib.util
import hashlib
import shutil
import struct
import subprocess
import sys
from pathlib import Path
from types import ModuleType


ROOT = Path(__file__).resolve().parents[2]
SIZE_T_MAX = (1 << (struct.calcsize("P") * 8)) - 1


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def require(haystack: str, needle: str, context: str) -> None:
    if needle not in haystack:
        raise AssertionError(f"Missing {needle!r} in {context}")


def reject(haystack: str, needle: str, context: str) -> None:
    if needle in haystack:
        raise AssertionError(f"Unexpected {needle!r} in {context}")


def function_body(source: str, signature: str) -> str:
    start = source.find(signature)
    if start == -1:
        raise AssertionError(f"Missing function signature {signature!r}")

    depth = 0
    for index in range(start, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]

    raise AssertionError(f"Could not find end of function {signature!r}")


def require_order(haystack: str, first: str, second: str, context: str) -> None:
    first_index = haystack.find(first)
    second_index = haystack.find(second)
    if first_index == -1 or second_index == -1:
        raise AssertionError(f"Missing ordered symbols {first!r} and/or {second!r} in {context}")
    if first_index >= second_index:
        raise AssertionError(f"Expected {first!r} before {second!r} in {context}")


def load_package_module() -> ModuleType:
    package_path = ROOT / "tools" / "build" / "package_nightly.py"
    spec = importlib.util.spec_from_file_location("package_nightly_for_openq4_pure_pack_test", package_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load package module from {package_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_test_file(path: Path, contents: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(contents)


def expect_runtime_error(message: str, callback, context: str) -> None:
    try:
        callback()
    except RuntimeError as exc:
        if message not in str(exc):
            raise AssertionError(f"Expected {message!r} in {context}, got {exc!r}") from exc
        return
    raise AssertionError(f"Expected RuntimeError for {context}")


def is_safe_download_path_model(path: str) -> bool:
    if not path or path.startswith(("/", "\\")) or "\\" in path or ":" in path:
        return False
    if any(ord(character) < 32 or character in '<>"|?*' for character in path):
        return False
    segments = path.split("/")
    if not all(
        segment not in ("", ".", "..")
        and not segment.startswith(" ")
        and not segment.endswith((".", " "))
        and not is_windows_device_path_segment_model(segment)
        for segment in segments
    ):
        return False
    return len(segments[-1]) > 4 and segments[-1].lower().endswith(".pk4")


def is_windows_device_path_segment_model(segment: str) -> bool:
    stem = segment.split(".", 1)[0].lower()
    if stem in ("con", "prn", "aux", "nul"):
        return True
    return len(stem) == 4 and stem[:3] in ("com", "lpt") and stem[3] in "123456789¹²³"


def bounded_download_write_model(
    bytes_written: int,
    size: int,
    nmemb: int,
    maximum_bytes: int,
) -> int | None:
    if size and nmemb > SIZE_T_MAX // size:
        return None
    byte_count = size * nmemb
    if bytes_written > SIZE_T_MAX - byte_count:
        return None
    if maximum_bytes and (
        bytes_written > maximum_bytes
        or byte_count > maximum_bytes - bytes_written
    ):
        return None
    return bytes_written + byte_count


def validate_filesystem_pure_pack_contract() -> None:
    source = read("src/framework/FileSystem.cpp")
    file_system_header = read("src/framework/FileSystem.h")
    md5_header = read("src/idlib/hashing/MD5.h")
    md5_source = read("src/idlib/hashing/MD5.cpp")
    async_client = read("src/framework/async/AsyncClient.cpp")
    async_server = read("src/framework/async/AsyncServer.cpp")
    session_menu = read("src/framework/Session_menu.cpp")
    curl_write = function_body(
        source,
        "size_t idFileSystemLocal::CurlWriteFunction(",
    )
    curl_progress = function_body(
        source,
        "int idFileSystemLocal::CurlProgressFunction(",
    )
    download_progress_box = function_body(
        session_menu,
        "void idSessionLocal::DownloadProgressBox(",
    )
    background_download = function_body(source, "dword BackgroundDownloadThread(")
    download_request = function_body(
        async_server,
        "void idAsyncServer::ProcessDownloadRequestMessage(",
    )
    download_path_helper = function_body(
        async_client,
        "static bool AsyncClient_IsSafeDownloadPath(",
    )
    download_device_helper = function_body(
        async_client,
        "static bool AsyncClient_IsWindowsDevicePathSegment(",
    )
    download_file_cleanup = function_body(
        async_client,
        "static void AsyncClient_CloseBackgroundDownloadFile(",
    )
    download_info = function_body(
        async_client,
        "void idAsyncClient::ProcessDownloadInfoMessage(",
    )
    download_handler = function_body(
        async_client,
        "void idAsyncClient::HandleDownloads(",
    )
    helper = function_body(source, "bool idFileSystemLocal::IsOpenQ4PurePack(")
    checksum_validator = function_body(source, "bool idFileSystemLocal::ValidateOpenQ4Paks(")
    misplaced_validator = function_body(source, "bool idFileSystemLocal::FindMisplacedOfficialPaks(")
    startup = function_body(source, "void idFileSystemLocal::Startup(")
    status = function_body(source, "pureStatus_t idFileSystemLocal::GetPackStatus(")

    require(source, '#include "openq4_paks_generated.h"', "filesystem generated pack checksum header")
    require(source, "IsOpenQ4PurePack", "filesystem pure-pack declaration")
    require(source, "ValidateOpenQ4Paks", "filesystem pack checksum declaration")
    require(helper, "OPENQ4_GAMEDIR", "openQ4 pure-pack directory check")
    require(helper, '"pak0.pk4"', "openQ4 pure-pack filename check")
    require(helper, '"pak1.pk4"', "openQ4 pure-pack filename check")
    require(helper, "IsGameDirPack( pak, OPENQ4_GAMEDIR )", "openQ4 pure-pack directory check")
    require(checksum_validator, "OPENQ4_PAK0_MD5", "openQ4 pak0 expected checksum")
    require(checksum_validator, "OPENQ4_PAK1_MD5", "openQ4 pak1 expected checksum")
    require(checksum_validator, "MD5_FileChecksum", "openQ4 pak0 actual checksum")
    require(checksum_validator, "FindGamePackByName( expected.name, OPENQ4_GAMEDIR )", "openQ4 pack lookup")
    require(checksum_validator, "checksum mismatch for %s/%s", "openQ4 pack checksum diagnostic")
    require(startup, "ValidateOpenQ4Paks( openQ4PakErrors )", "startup pack checksum validation")
    require(startup, "openQ4 runtime content packs in '%s' are missing or modified", "startup pack checksum fatal")
    require(startup, "openQ4 runtime directory '%s' is missing a compatible mod.json", "startup mod manifest fatal")
    require(startup, "Retail Quake 4 media pk4 files must be installed in '%s', not '%s'.", "startup misplaced retail pk4 fatal")
    require(startup, "Put pak001.pk4 through pak022.pk4 in that folder", "startup retail pk4 location guidance")
    require(startup, "Do not put retail pk4 files in '%s'", "startup baseoq4 retail pk4 warning")
    require(misplaced_validator, "FindGamePackByName( info->name, OPENQ4_GAMEDIR )", "misplaced retail pk4 baseoq4 lookup")
    require(misplaced_validator, "with checksum 0x%08x but belongs in %s", "misplaced retail pk4 checksum diagnostic")
    require(misplaced_validator, "was found in both %s and %s; remove the copy from %s", "misplaced duplicate retail pk4 diagnostic")
    require(md5_header, "MD5_FileChecksum", "MD5 file checksum declaration")
    require(md5_source, "MD5_FileChecksum", "MD5 file checksum implementation")
    require(md5_source, "fopen( path, \"rb\" )", "MD5 file checksum binary read")
    require(
        md5_source,
        'static_assert( sizeof( unsigned int ) == 4, "MD5 requires 32-bit digest words" );',
        "fixed-width MD5 digest contract",
    )
    require(md5_source, "unsigned int\tdigest[4];", "fixed-width MD5 digest storage")
    require(md5_source, "unsigned int\tval;", "fixed-width MD5 checksum accumulator")
    require(md5_source, "val = digest[0] ^ digest[1] ^ digest[2] ^ digest[3];", "MD5 word folding")
    require(md5_source, "memset( ctx, 0, sizeof( *ctx ) );", "complete MD5 context clearing")
    reject(md5_source, "unsigned long\tdigest[4];", "LP64-unsafe MD5 digest storage")
    reject(md5_source, "memset( ctx, 0, sizeof( ctx ) );", "pointer-sized MD5 context clearing")

    require(file_system_header, "expectedSize;", "immutable URL download-size limit")
    require(curl_write, "nmemb > maximumSize / size", "libcurl callback multiplication guard")
    require(
        curl_write,
        "context->bytesWritten > maximumSize - byteCount",
        "libcurl callback cumulative-size guard",
    )
    require(
        curl_write,
        "byteCount > context->maximumBytes - context->bytesWritten",
        "libcurl callback advertised-size guard",
    )
    require(curl_write, '"download exceeds advertised size"', "oversized download diagnostic")
    require(
        curl_write,
        "fwrite( ptr, 1, byteCount",
        "libcurl byte-count write callback contract",
    )
    require(curl_write, "context->bytesWritten += written;", "download byte accounting")
    require(curl_write, "return written;", "libcurl exact write-result contract")
    require(curl_progress, "dltotal >= idMath::INT_MAX", "download-total progress narrowing guard")
    require(curl_progress, "dlnow >= idMath::INT_MAX", "download-current progress narrowing guard")
    require(curl_progress, "static_cast<int>( dltotal )", "checked download-total conversion")
    require(curl_progress, "static_cast<int>( dlnow )", "checked download-current conversion")
    require(
        curl_progress,
        "bgl->url.dltotal = bgl->url.expectedSize;",
        "package progress uses its advertised total",
    )
    require(
        curl_progress,
        "Min( reportedNow, bgl->url.expectedSize )",
        "package progress is capped at its advertised total",
    )
    reject(curl_progress, "bgl->url.dltotal = dltotal;", "unchecked download-total conversion")
    reject(curl_progress, "bgl->url.dlnow = dlnow;", "unchecked download-current conversion")
    require(
        download_progress_box,
        "static_cast<int64>( dlnow ) * ( progress_end - progress_start )",
        "download progress percentage overflow guard",
    )
    require(source, "~idScopedCurlEasySession()", "libcurl session lifetime guard")
    require(source, "curl_easy_cleanup( session );", "libcurl session cleanup")
    require_order(
        background_download,
        "idScopedCurlEasySession scopedSession( session );",
        "CURLOPT_ERRORBUFFER",
        "libcurl session guard before fallible options",
    )
    require(background_download, "error_buf[ 0 ] = '\\0';", "initialized libcurl error buffer")
    require(
        background_download,
        "bgl->url.expectedSize > 0 ? static_cast<size_t>( bgl->url.expectedSize ) : 0",
        "immutable download limit capture",
    )
    require(
        background_download,
        "curlDownloadContext_t downloadContext = { bgl, maximumBytes, 0 };",
        "per-transfer byte accounting context",
    )
    require(
        background_download,
        "CURLOPT_WRITEDATA, &downloadContext",
        "libcurl bounded write context ownership",
    )
    require_order(
        background_download,
        "curlDownloadContext_t downloadContext = { bgl, maximumBytes, 0 };",
        "bgl->url.dltotal = 0;",
        "download limit capture before mutable progress reset",
    )
    require(
        background_download,
        "downloadContext.bytesWritten != downloadContext.maximumBytes",
        "successful package transfer exact-size verification",
    )
    require(
        background_download,
        "bgl->url.dlstatus = CURLE_PARTIAL_FILE;",
        "short package transfer failure status",
    )
    require(
        background_download,
        "error_buf[ 0 ] != '\\0' ? error_buf : curl_easy_strerror( ret )",
        "libcurl fallback error diagnostic",
    )

    require(download_path_helper, "segmentStart[ 0 ] == ' '", "download path leading-space rejection")
    require(
        download_path_helper,
        "AsyncClient_IsWindowsDevicePathSegment( segmentStart, segmentLength )",
        "download path device-name rejection",
    )
    require(download_device_helper, 'idStr::Icmpn( segment, "con", 3 )', "CON device-name rejection")
    require(download_device_helper, 'idStr::Icmpn( segment, "com", 3 )', "COM device-name rejection")
    require(download_device_helper, "digit == 0xC2", "UTF-8 superscript device-name rejection")
    require(download_device_helper, "digit == 0xB9", "Windows-1252 superscript device-name rejection")
    require_order(
        download_file_cleanup,
        "idFile *file = download.f;",
        "download.f = NULL;",
        "background download file ownership transfer",
    )
    require_order(
        download_file_cleanup,
        "download.f = NULL;",
        "fileSystem->CloseFile( file );",
        "background download pointer detachment before file close",
    )
    require(download_file_cleanup, "if ( file != NULL )", "idempotent background download file cleanup")

    checksum_vectors = {
        b"": 0x3B75655E,
        b"abc": 0x275FA452,
        b"openQ4": 0x8A8BAE9B,
    }
    for payload, expected in checksum_vectors.items():
        digest_words = struct.unpack("<4I", hashlib.md5(payload).digest())
        actual = digest_words[0] ^ digest_words[1] ^ digest_words[2] ^ digest_words[3]
        if actual != expected:
            raise AssertionError(
                f"MD5 block-checksum semantics changed for {payload!r}: "
                f"expected 0x{expected:08x}, got 0x{actual:08x}"
            )

    require(async_client, "Client decl checksum: 0x%08x", "client decl checksum diagnostic")
    require(async_server, "Server decl checksum: 0x%08x", "server decl checksum diagnostic")
    require(async_server, "client=0x%08x server=0x%08x (non-pure)", "non-pure mismatch diagnostic")
    require(async_server, "client=0x%08x server=0x%08x (pure)", "pure mismatch diagnostic")
    require(
        download_request,
        "dlSize[ MAX_PURE_PAKS ] = {};",
        "download response size initialization for the no-game-pak slot",
    )
    require(
        download_request,
        "totalDlSize > idMath::INT_MAX - dlSize[ i ]",
        "download response total-size overflow guard",
    )
    require(
        download_request,
        "pakURLs.Num() > pakNames.Num()",
        "download response URL-count bounds guard",
    )
    require_order(
        download_request,
        "pakURLs.Num() > pakNames.Num()",
        "for ( i = 0; i < pakURLs.Num(); i++ )",
        "download response URL-count validation before indexed access",
    )
    require(download_path_helper, "path[ 0 ] == '/'", "absolute server download path rejection")
    require(download_path_helper, "path[ 0 ] == '\\\\'", "rooted backslash server download path rejection")
    require(download_path_helper, "c == '\\\\' || c == ':'", "backslash and drive-path rejection")
    require(download_path_helper, "static_cast<unsigned char>( c ) < 32", "control-character path rejection")
    require(download_path_helper, "c == '<'", "Windows-reserved punctuation rejection")
    require(download_path_helper, "c == '*'", "Windows-reserved punctuation rejection")
    require(download_path_helper, "segmentLength == 0", "empty download path segment rejection")
    require(download_path_helper, "segmentStart[ 0 ] == '.'", "dot download path segment rejection")
    require(download_path_helper, "segmentStart[ 1 ] == '.'", "parent download path segment rejection")
    require(
        download_path_helper,
        "segmentStart[ segmentLength - 1 ] == '.'",
        "Windows trailing-dot path rejection",
    )
    require(
        download_path_helper,
        "segmentStart[ segmentLength - 1 ] == ' '",
        "Windows trailing-space path rejection",
    )
    require(download_path_helper, "segmentLength > 4", "download package filename requirement")
    require(
        download_path_helper,
        'idStr::Icmp( scan - 4, ".pk4" ) == 0',
        "case-insensitive PK4 download extension requirement",
    )

    download_yes = download_info[
        download_info.find("if ( pakDl == SERVER_PAK_YES )") :
        download_info.find("} else if ( pakDl == SERVER_PAK_NO )")
    ]
    require(download_yes, "AsyncClient_IsSafeDownloadPath( buf )", "server download path validation")
    require_order(
        download_yes,
        "msg.ReadString( buf, MAX_STRING_CHARS );",
        "AsyncClient_IsSafeDownloadPath( buf )",
        "server download path validation after decode",
    )
    require_order(
        download_yes,
        "AsyncClient_IsSafeDownloadPath( buf )",
        "entry.filename = buf;",
        "server download path validation before storage",
    )
    require(download_yes, "entry.size <= 0", "non-positive server download-size rejection")
    require(
        download_yes,
        "totalDlSize > idMath::INT_MAX - entry.size",
        "server download total-size overflow guard",
    )
    require_order(
        download_yes,
        "totalDlSize > idMath::INT_MAX - entry.size",
        "totalDlSize += entry.size;",
        "server download size validation before accumulation",
    )
    invalid_download_type = download_info[
        download_info.find("} else if ( pakDl != SERVER_PAK_END )") :
        download_info.find("} while ( pakDl != SERVER_PAK_END )")
    ]
    require(
        invalid_download_type,
        "server sent invalid download entry type",
        "invalid download discriminator diagnostic",
    )
    require(invalid_download_type, "dlList.Clear();", "invalid download discriminator cleanup")
    require(invalid_download_type, "return;", "invalid download discriminator fail-closed return")
    reject(download_info, "assert( pakDl == SERVER_PAK_END );", "release-only download discriminator validation")

    update_setup = download_handler[
        download_handler.find("fileSystem->OpenFileWrite( updateFile )") :
        download_handler.find("updateState = UPDATE_DLING;")
    ]
    require(update_setup, "backgroundDownload.url.expectedSize = 0;", "unrestricted updater download")
    package_setup = download_handler[
        download_handler.find("fileSystem->MakeTemporaryFile( )") :
        download_handler.find("session->DownloadProgressBox( &backgroundDownload, dltitle")
    ]
    require(
        package_setup,
        "backgroundDownload.url.expectedSize = dlList[ 0 ].size;",
        "package advertised-size limit",
    )
    require(package_setup, "backgroundDownload.url.dltotal = 0;", "progress total initialization")
    reject(
        package_setup,
        "backgroundDownload.url.dltotal = dlList[ 0 ].size;",
        "advertised-size limit stored in mutable progress",
    )
    require_order(
        package_setup,
        "backgroundDownload.url.expectedSize = dlList[ 0 ].size;",
        "fileSystem->BackgroundDownload( &backgroundDownload );",
        "package size limit set before worker handoff",
    )

    if bounded_download_write_model(0, 2, 5, 10) != 10:
        raise AssertionError("Bounded download model rejected an exact-size write")
    if bounded_download_write_model(9, 1, 2, 10) is not None:
        raise AssertionError("Bounded download model accepted a body above its advertised size")
    if bounded_download_write_model(0, 2, SIZE_T_MAX // 2 + 1, 0) is not None:
        raise AssertionError("Bounded download model accepted overflowing callback dimensions")
    if bounded_download_write_model(SIZE_T_MAX, 1, 1, 0) is not None:
        raise AssertionError("Bounded download model accepted overflowing cumulative bytes")
    if bounded_download_write_model(9, 1, 2, 0) != 11:
        raise AssertionError("Updater download model unexpectedly applied a package-size limit")

    require_order(
        download_handler,
        "existingDestination = fileSystem->OpenExplicitFileRead( finalPath );",
        "fileSystem->CreateOSPath( finalPath );",
        "existing download destination check before directory creation",
    )
    existing_destination_failure = download_handler[
        download_handler.find("if ( existingDestination )") :
        download_handler.find("fileSystem->CreateOSPath( finalPath );")
    ]
    require(
        existing_destination_failure,
        "fileSystem->CloseFile( existingDestination );",
        "existing download destination probe cleanup",
    )
    require(
        existing_destination_failure,
        "refusing to replace existing download destination",
        "existing download destination diagnostic",
    )
    require(
        existing_destination_failure,
        "AsyncClient_CloseBackgroundDownloadFile( backgroundDownload );",
        "existing destination temporary-file cleanup",
    )
    require(existing_destination_failure, "dlList.Clear();", "existing destination download-list cleanup")

    require_order(
        download_handler,
        "saveas = fileSystem->OpenExplicitFileWrite( finalPath );",
        "if ( !saveas )",
        "download destination open failure handling",
    )
    require_order(
        download_handler,
        "if ( !saveas )",
        "saveas->Write( buf, readlen );",
        "download destination null guard",
    )
    destination_failure = download_handler[
        download_handler.find("if ( !saveas )") :
        download_handler.find("buf = (byte*)Mem_Alloc( CHUNK_SIZE );")
    ]
    require(
        destination_failure,
        "AsyncClient_CloseBackgroundDownloadFile( backgroundDownload );",
        "failed destination temporary-file cleanup",
    )
    require(destination_failure, "dlList.Clear();", "failed download-list cleanup")
    require(destination_failure, '"#str_07215"', "localized download failure message")
    require(
        download_handler,
        "fileSystem->RemoveExplicitFile( finalPath );",
        "checksum failure removes only the verified download destination",
    )

    update_destination = download_handler[
        download_handler.find("fileSystem->OpenFileWrite( updateFile )") :
        download_handler.find("dltotal = 0;")
    ]
    require(update_destination, "if ( f == NULL )", "update destination null guard")
    require(update_destination, "updateState = UPDATE_DONE;", "failed update state cleanup")
    require(update_destination, "SendVersionDLUpdate( 2 );", "failed update telemetry")
    require(update_destination, '"#str_04335"', "localized update failure message")
    require(update_destination, "updateFallback.Length()", "failed update fallback")
    require(update_destination, "return;", "failed update early return")

    update_download_result = download_handler[
        download_handler.find("if ( backgroundDownload.url.status == DL_DONE )") :
        download_handler.find("} else if ( dlList.Num() )")
    ]
    if update_download_result.count("AsyncClient_CloseBackgroundDownloadFile( backgroundDownload );") != 2:
        raise AssertionError("Update download success and failure paths must each release their owned file")

    successful_copy_cleanup = download_handler[
        download_handler.find("while ( remainlen )") :
        download_handler.find("fileSystem->CloseFile( saveas );")
    ]
    require(
        successful_copy_cleanup,
        "AsyncClient_CloseBackgroundDownloadFile( backgroundDownload );",
        "successful package download temporary-file cleanup",
    )

    failed_download_cleanup = download_handler[
        download_handler.find('common->Warning( "download failed:') :
        download_handler.find("pakCount++;")
    ]
    require(
        failed_download_cleanup,
        "AsyncClient_CloseBackgroundDownloadFile( backgroundDownload );",
        "failed or cancelled package download temporary-file cleanup",
    )
    require_order(
        failed_download_cleanup,
        "AsyncClient_CloseBackgroundDownloadFile( backgroundDownload );",
        "dlList.Clear();",
        "failed package download file cleanup before return",
    )
    reject(download_handler, "fileSystem->CloseFile( f );", "direct background download file close")
    reject(
        download_handler,
        "fileSystem->CloseFile( backgroundDownload.f );",
        "direct background download member close",
    )
    cleanup_call = "AsyncClient_CloseBackgroundDownloadFile( backgroundDownload );"
    if download_handler.count(cleanup_call) != 6:
        raise AssertionError("Every background download completion path must release its file exactly once")

    valid_download_paths = (
        "baseoq4/example.pk4",
        "baseoq4/downloads/example.pk4",
        "baseoq4/downloads/example.PK4",
        "mods/example.pk4",
        "example.pk4",
    )
    invalid_download_paths = (
        "",
        "/baseoq4/example.pk4",
        "\\baseoq4\\example.pk4",
        "C:/baseoq4/example.pk4",
        "baseoq4\\example.pk4",
        "baseoq4/mixed\\example.pk4",
        ".",
        "..",
        "./example.pk4",
        "../example.pk4",
        "baseoq4/./example.pk4",
        "baseoq4/../example.pk4",
        "baseoq4/.. /example.pk4",
        "baseoq4/trailing./example.pk4",
        "baseoq4/trailing /example.pk4",
        "baseoq4//example.pk4",
        "baseoq4/example.pk4/",
        "baseoq4/example.pk4.",
        "baseoq4/example.pk4 ",
        " baseoq4/example.pk4",
        "baseoq4/ downloads/example.pk4",
        "baseoq4/example:alternate.pk4",
        "baseoq4/example?.pk4",
        "baseoq4/example*.pk4",
        "baseoq4/example|alternate.pk4",
        "baseoq4/example\x01.pk4",
        "baseoq4/example.zip",
        "baseoq4/.pk4",
        "CON.pk4",
        "baseoq4/prn/example.pk4",
        "baseoq4/AUX.txt/example.pk4",
        "baseoq4/nul/example.pk4",
        "baseoq4/COM1.pk4",
        "baseoq4/lpt9/example.pk4",
        "baseoq4/COM¹.pk4",
        "baseoq4/LPT²/example.pk4",
        "baseoq4/com³.txt/example.pk4",
    )
    for path in valid_download_paths:
        if not is_safe_download_path_model(path):
            raise AssertionError(f"Valid server download path rejected by model: {path!r}")
    for path in invalid_download_paths:
        if is_safe_download_path_model(path):
            raise AssertionError(f"Unsafe server download path accepted by model: {path!r}")

    require(status, "IsOpenQ4PurePack( pak )", "GetPackStatus openQ4 pure-pack check")
    require_order(
        status,
        "IsOpenQ4PurePack( pak )",
        "FindOfficialPk4Info",
        "GetPackStatus openQ4 pure-pack precedence",
    )
    require_order(
        status,
        "IsOpenQ4PurePack( pak )",
        "// check content for PURE_NEVER",
        "GetPackStatus openQ4 pure-pack precedence",
    )

    openq4_check = status[
        status.find("if ( IsOpenQ4PurePack( pak ) )") :
        status.find("// Keep the stock Quake 4 base media")
    ]
    require(openq4_check, "pak->pureStatus = PURE_ALWAYS;", "openQ4 pure-pack status")
    require(openq4_check, "return PURE_ALWAYS;", "openQ4 pure-pack return")


def validate_install_error_console_contract() -> None:
    posix_main = read("src/sys/posix/posix_main.cpp")
    posix_signal = read("src/sys/posix/posix_signal.cpp")
    posix_console = read("src/sys/posix/posix_syscon.cpp")
    posix_header = read("src/sys/posix/posix_public.h")
    win_console = read("src/sys/win32/win_syscon.cpp")
    console_theme = read("src/sys/sys_console_theme.h")

    require(posix_header, "Posix_ConsoleSetFatalError", "POSIX fatal console declaration")
    require(posix_header, "Posix_ConsoleFatalErrorWait", "POSIX fatal console declaration")
    require(posix_main, "Sys_SetFatalError( text );", "POSIX Sys_Error fatal banner update")
    require(posix_main, "Sys_Printf( \"Sys_Error: %s\\n\", text );", "POSIX Sys_Error console log text")
    require(posix_main, "Posix_ConsoleFatalErrorWait();", "POSIX Sys_Error visible console wait")
    require(posix_signal, "Posix_ConsoleSetFatalError( fatalError );", "POSIX fatal signal bridge")
    require(posix_console, "POSIX_CONSOLE_STATUS_HEIGHT", "POSIX console status strip")
    require(posix_console, "Posix_ConsoleDrawStatus", "POSIX console status rendering")
    reject(posix_console, "statusText = \"ERROR: \";", "POSIX console fatal status text")
    require(posix_console, "statusText.Append( scan, 1 );", "POSIX console fatal status text")
    # Presentation moved to the shared cross-platform theme; see
    # tools/tests/system_console_presentation.py for the full contract.
    require(console_theme, '#define SYSCON_STATUS_READY_TEXT\t"System console ready"', "shared console ready status text")
    require(posix_console, "statusText = SYSCON_STATUS_READY_TEXT;", "POSIX console ready status")
    require(posix_console, "s_consoleWindow.forceFatalWindow = true;", "POSIX fatal console forced visibility")
    require(
        posix_console,
        "if ( !s_consoleWindow.forceFatalWindow &&\n\t\t ( cvarSystem == NULL || !cvarSystem->IsInitialized() || !sys_consoleWindow.GetBool() ) )",
        "POSIX fatal console avoids released cvar storage",
    )
    require(posix_console, "s_consoleWindow.exitRequested = true;", "POSIX fatal console quit/close exit")
    require(win_console, "SYSCON_STATUS_READY_TEXT", "Windows console ready status")
    require(win_console, "SYSCON_WIN_RGB(PANEL)", "Windows console status background color")
    require(win_console, "SYSCON_WIN_RGB(TEXT)", "Windows console status text color")
    require(win_console, "SYSCON_WIN_RGB(ALERT_PANEL)", "Windows console fatal status background color")
    require(win_console, "SetWindowText(s_wcd.hwndErrorBox, s_wcd.errorString);", "Windows console status text update")


def validate_packager_pure_pack_contract() -> None:
    package = load_package_module()
    pak_helper = read("tools/build/openq4_pak.py")
    packager = read("tools/build/package_nightly.py")
    work = ROOT / ".tmp" / "openq4-pure-pack-contract"

    require(pak_helper, "DETERMINISTIC_ZIP_TIMESTAMP", "deterministic zip metadata")
    require(pak_helper, "PAK1_NAME", "pak1 helper name")
    require(pak_helper, "OPENQ4_REQUIRED_PK4_FILES_BY_PACK", "per-pack required files")
    require(pak_helper, "OPENQ4_PK4_FORBIDDEN_FILES", "package pure-pack marker guard")
    require(pak_helper, '"binary.conf"', "package pure-pack binary marker guard")
    require(pak_helper, '"addon.conf"', "package pure-pack addon marker guard")
    require(pak_helper, "must remain a pure runtime pack", "package pure-pack marker diagnostic")
    require(pak_helper, "hashlib.md5", "pack full-file checksum")
    require(pak_helper, "copy_game_pk4", "package staged pack copy helper")
    require(packager, "from openq4_pak import", "release packager shared pak helper")
    require(packager, "OPENQ4_PACK_NAMES", "release packager pack list")
    require(packager, "for pak_name in OPENQ4_PACK_NAMES", "release packager iterates openQ4 packs")
    require(packager, "staged_game_pk4_path", "release packager staged pack preference")
    require(packager, "copy_game_pk4(staged_game_pk4_path, game_pk4_path, pak_name=pak_name)", "release packager staged pack copy")
    require(packager, "md5 {pk4_result.md5_hex}", "release packager checksum summary")

    shutil.rmtree(work, ignore_errors=True)
    try:
        for pak_name in ("pak0.pk4", "pak1.pk4"):
            for marker in ("binary.conf", "addon.conf"):
                shutil.rmtree(work, ignore_errors=True)
                install_game_dir = work / "baseoq4"
                destination_pk4 = work / pak_name
                write_test_file(install_game_dir / marker, b"marker\n")
                expect_runtime_error(
                    "must remain a pure runtime pack",
                    lambda: package.create_game_pk4(install_game_dir, destination_pk4, pak_name),
                    f"{pak_name} marker rejection for {marker}",
                )
    finally:
        shutil.rmtree(work, ignore_errors=True)


def validate_build_pak0_contract() -> None:
    meson = read("meson.build")
    baseoq4_meson = read("content/baseoq4/meson.build")
    build_pak0 = read("tools/build/build_pak0.py")
    build_openq4_pack = read("tools/build/build_openq4_pack.py")
    generate_pak_header = read("tools/build/generate_pak_header.py")
    write_pak_manifest = read("tools/build/write_pak_manifest.py")
    pak_helper = read("tools/build/openq4_pak.py")
    install_guard = read("tools/build/check_staged_content_edits.py")
    windows_runtime = read("tools/build/windows_runtime.py")
    validator = read("tools/validation/openq4_validate.py")
    work = ROOT / ".tmp" / "openq4-pak0-build-contract"

    require(meson, "custom_target(", "Meson pak0 build target")
    require(meson, "'openq4_pak0'", "Meson openQ4 pak0 build target name")
    require(meson, "'openq4_pak1'", "Meson openQ4 pak1 build target name")
    require(meson, "'openq4_paks_generated_header'", "Meson generated pack checksum target name")
    require(meson, "'openq4_pak0_source_manifest'", "Meson pak0 source manifest target")
    require(meson, "'openq4_pak1_source_manifest'", "Meson pak1 source manifest target")
    require(meson, "write_pak_manifest.py", "Meson pack source manifest refresh")
    require(meson, "build_openq4_pack.py", "Meson single-pack build script")
    require(meson, "generate_pak_header.py", "Meson pack header generation script")
    require(meson, "'openq4_paks_generated.h'", "Meson generated pack checksum header")
    require(meson, "input: openq4_pak0_source_manifest", "Meson pak0 depends on source manifest")
    require(meson, "input: openq4_pak1_source_manifest", "Meson pak1 depends on source manifest")
    require(meson, "--manifest", "Meson pack target consumes source manifest")
    require(meson, "build_by_default: true", "Meson pack default build")
    require(meson, "build_always_stale: true", "Meson source manifests rescan pack directories")
    reject(meson, "openq4_pak0_source_paths", "Meson pak0 must not bake a configured source-file list")
    reject(meson, "openq4_pak1_source_paths", "Meson pak1 must not bake a configured source-file list")
    require(meson, "install: true", "Meson pack install")
    require(meson, "install: false", "Meson does not install generated header")
    require(meson, "install_dir: install_game_dir", "Meson installs generated packs")
    require(meson, "openq4_engine_sources += openq4_paks_generated_header", "engine depends on pack checksum header")
    require_order(meson, "'openq4_pak0'", "'openq4_paks_generated_header'", "packs before checksum header")
    require_order(meson, "'openq4_paks_generated_header'", "openq4_engine_sources += openq4_paks_generated_header", "checksum header before engine sources")

    require(baseoq4_meson, "baseoq4_manifest", "loose mod.json install")
    reject(baseoq4_meson, "install_subdir(", "baseoq4 content should be inside openQ4 PK4s")
    reject(baseoq4_meson, "'openq4_defaults.cfg'", "baseoq4 loose config install")
    reject(baseoq4_meson, "'default.cfg'", "baseoq4 loose default config install")

    require(pak_helper, "OPENQ4_PAK0_MD5", "generated pak0 checksum macro")
    require(pak_helper, "OPENQ4_PAK1_MD5", "generated pak1 checksum macro")
    require(build_pak0, "format_openq4_paks_header", "standalone pack builder uses shared header formatter")
    require(build_pak0, "create_game_pk4", "build pak0 helper")
    require(build_pak0, "--pak0-stage-out", "builddir direct-run pak0 staging")
    require(build_pak0, "--pak1-stage-out", "builddir direct-run pak1 staging")
    require(build_openq4_pack, "--pak-name", "single-pack build script pack selection")
    require(build_openq4_pack, "create_game_pk4", "single-pack build script helper")
    require(build_openq4_pack, "--manifest", "single-pack build script manifest dependency")
    require(build_openq4_pack, "--stage-out", "single-pack builddir direct-run staging")
    require(generate_pak_header, "format_openq4_paks_header", "generated pack header shared formatter")
    require(generate_pak_header, "inspect_game_pk4", "generated pack header validates built packs")
    require(pak_helper, "format_pk4_source_manifest", "pack source manifest matches packer filtering")
    require(write_pak_manifest, "format_pk4_source_manifest", "Meson pack manifest source list matches packer filtering")
    require(write_pak_manifest, "write_text_if_changed", "Meson pack manifest avoids unnecessary downstream rebuilds")
    require(install_guard, "STALE_LOOSE_ROOT_FILES", "install guard stale loose root files")
    require(install_guard, "STALE_LOOSE_SUBDIRS", "install guard stale loose content dirs")
    require(install_guard, '"default.cfg"', "install guard stale loose default config")
    require(install_guard, '"env"', "install guard stale loose env content")
    require(install_guard, '"scripts"', "install guard stale loose map scripts")
    require(install_guard, "assert_inside", "install guard deletion containment")
    require(install_guard, "shutil.rmtree", "install guard stale loose directory pruning")
    require(windows_runtime, "build_game_pk4s", "Windows direct-run pack staging")
    require(windows_runtime, '"pak1.pk4"', "Windows direct-run pak1 destination")
    require(validator, '"pak0.pk4"', "staged payload requires pak0.pk4")
    require(validator, '"pak1.pk4"', "staged payload requires pak1.pk4")
    require(validator, "STAGED_FORBIDDEN_LOOSE_GAME_PATHS", "staged payload forbids stale loose content")
    require(validator, '"openq4_defaults.cfg"', "staged payload forbids loose defaults")
    require(validator, "must live inside openQ4 PK4s", "staged payload stale loose diagnostic")

    shutil.rmtree(work, ignore_errors=True)
    try:
        pak0_source_dir = work / "source" / "baseoq4" / "pak0"
        pak1_source_dir = work / "source" / "baseoq4" / "pak1"
        pak0_required_files = [
            "glprogs/smaa_blend.fs",
            "glprogs/smaa_blend.vs",
            "glprogs/smaa_edge.fs",
            "glprogs/smaa_edge.vs",
            "glprogs/smaa_weights.fs",
            "glprogs/smaa_weights.vs",
            "materials/postprocess_openq4.mtr",
        ]
        pak1_required_files = [
            "gfx/guis/loadscreens/generic.dds",
            "gfx/guis/loadscreens/generic.tga",
        ]
        for relative_path in pak0_required_files:
            write_test_file(pak0_source_dir / relative_path, f"{relative_path}\n".encode("utf-8"))
        for relative_path in pak1_required_files:
            write_test_file(pak1_source_dir / relative_path, f"{relative_path}\n".encode("utf-8"))

        pak0_out = work / "pak0.pk4"
        pak1_out = work / "pak1.pk4"
        header_out = work / "openq4_paks_generated.h"
        pak0_stage_out = work / "stage" / "baseoq4" / "pak0.pk4"
        pak1_stage_out = work / "stage" / "baseoq4" / "pak1.pk4"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "build" / "build_pak0.py"),
                "--pak0-source-dir",
                str(pak0_source_dir),
                "--pak1-source-dir",
                str(pak1_source_dir),
                "--pak0-out",
                str(pak0_out),
                "--pak1-out",
                str(pak1_out),
                "--header-out",
                str(header_out),
                "--pak0-stage-out",
                str(pak0_stage_out),
                "--pak1-stage-out",
                str(pak1_stage_out),
            ],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        pak0_digest = hashlib.md5(pak0_out.read_bytes()).hexdigest()
        pak1_digest = hashlib.md5(pak1_out.read_bytes()).hexdigest()
        header = header_out.read_text(encoding="utf-8")
        require(header, f'#define OPENQ4_PAK0_MD5 "{pak0_digest}"', "generated pak0 checksum header")
        require(header, f'#define OPENQ4_PAK1_MD5 "{pak1_digest}"', "generated pak1 checksum header")
        require(header, "#define OPENQ4_PAK0_FILE_COUNT 7", "generated pak0 file count")
        require(header, "#define OPENQ4_PAK1_FILE_COUNT 2", "generated pak1 file count")
        if pak0_out.read_bytes() != pak0_stage_out.read_bytes():
            raise AssertionError("Staged pak0.pk4 does not match generated pak0.pk4")
        if pak1_out.read_bytes() != pak1_stage_out.read_bytes():
            raise AssertionError("Staged pak1.pk4 does not match generated pak1.pk4")
    finally:
        shutil.rmtree(work, ignore_errors=True)


def validate_validation_coverage() -> None:
    validator = read("tools/validation/openq4_validate.py")
    push = read(".github/workflows/push-verification.yml")
    commit = read(".github/workflows/commit-validation.yml")

    for haystack, context in (
        (validator, "validation runner"),
        (push, "push verification workflow"),
        (commit, "commit validation workflow"),
    ):
        require(haystack, "openq4_pure_pack.py", context)

    for haystack, context in (
        (push, "push verification workflow"),
        (commit, "commit validation workflow"),
    ):
        require(haystack, "build_pak0.py", context)
        require(haystack, "build_openq4_pack.py", context)
        require(haystack, "generate_pak_header.py", context)
        require(haystack, "list_pak_sources.py", context)
        require(haystack, "write_pak_manifest.py", context)
        require(haystack, "openq4_pak.py", context)


def main() -> None:
    validate_filesystem_pure_pack_contract()
    validate_install_error_console_contract()
    validate_packager_pure_pack_contract()
    validate_build_pak0_contract()
    validate_validation_coverage()
    print("openq4_pure_pack: ok")


if __name__ == "__main__":
    main()
