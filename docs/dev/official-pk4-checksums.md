# Official Quake 4 PK4 Checksums (q4base)

This table captures the PK4 checksums loaded from official installed game directories:

- Primary install path: `C:\Program Files (x86)\Steam\steamapps\common\Quake 4\q4base`
- Additional source: issue #54 startup log from a Spanish physical/DVD install
- Log source: `logs/openq4.log` startup lines (`Loaded pk4 ... with checksum ...`) under `fs_savepath\<gameDir>\`
- Checksum format: engine PK4 checksum (`MD4` of zip-entry CRC list, as computed in `src/framework/FileSystem.cpp`)

openQ4 ignores the retail game-binary PK4 archives (`game000.pk4` through `game300.pk4`, plus `gamex*.pk4` variants) because it ships its own game modules. They are not required and are not verified.

## Required official baseline

These core retail media PK4s are required by openQ4 startup validation (`fs_validateOfficialPaks 1`, default):

| PK4 | Checksum |
|---|---|
| `pak001.pk4` | `0xf2cbc998` |
| `pak002.pk4` | `0x7f8d80d1` |
| `pak003.pk4` | `0x1b57b207` |
| `pak004.pk4` | `0x385aa578` |
| `pak005.pk4` | `0x60d50a1d` |
| `pak006.pk4` | `0x9099ed11` |
| `pak007.pk4` | `0xaf301fff` |
| `pak008.pk4` | `0x4ac6f6d9` |
| `pak009.pk4` | `0x36030c7d` |
| `pak010.pk4` | `0x4b80fbda` |
| `pak011.pk4` | `0x8acf4cfa` |
| `pak012.pk4` | `0xbe4120b0` |
| `pak013.pk4` | `0x6ad67f40` |
| `pak014.pk4` | `0xee51cd59` |
| `pak015.pk4` | `0xf5bf4e0c` |
| `pak016.pk4` | `0x2196f58c` |
| `pak017.pk4` | `0x91118a35` |
| `pak018.pk4` | `0x98a14f03` |
| `pak019.pk4` | `0xbc82ac79` |
| `pak020.pk4` | `0xce74cda5` |
| `pak021.pk4` | `0x2ba6e70c` |
| `pak022.pk4` | `0x4e390eec` |

## Optional official PK4s detected

These PK4s are recognized when present, but missing files do not block startup. `pak023.pk4` through `pak025.pk4` contain official patch/menu splash media rather than core campaign or multiplayer assets required by openQ4.

At least one unsuffixed `zpak_<language>.pk4` base archive is needed for character dialogue: the shared `pak001.pk4` through `pak022.pk4` baseline contains the sound declarations and lip-sync data, but not the localized voice audio itself. Numbered files such as `zpak_english_01.pk4` are patch archives and do not replace that base media. Client startup warns when no recognized unsuffixed retail language-pack filename is mounted. This check identifies the known language name and base filename; it does not claim that the archive contents are complete. The absence remains non-fatal so dedicated servers and alternate physical/localized editions are not tied to one specific language archive or checksum.

| PK4 | Checksum |
|---|---|
| `pak023.pk4` | `0x7c1fd3a5` |
| `pak024.pk4` | `0x5546d551` |
| `pak025.pk4` | `0xcaeec1fd` |
| `q4cmp_pak001.pk4` | `0xd0813943` |
| `zpak_english.pk4` | `0x5868f530` |
| `zpak_english_01.pk4` | `0xd9f04b8b` |
| `zpak_english_02.pk4` | `0x9dbd91fd` |
| `zpak_english_03.pk4` | `0x02eb6ad8` |
| `zpak_english_04.pk4` | `0xd3fefaa1` |
| `zpak_english_05.pk4` | `0x8596af60` |
| `zpak_spanish.pk4` | `0xb706e2b8` |
