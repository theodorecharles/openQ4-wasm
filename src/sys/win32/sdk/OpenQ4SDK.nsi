SetCompressor lzma

; HM NIS Edit Wizard helper defines
!define PRODUCT_NAME "openQ4 SDK"
!ifndef PRODUCT_VERSION
!searchparse /file /noerrors "..\..\..\..\meson.build" `version: '` PRODUCT_VERSION `'`
!endif
!ifndef PRODUCT_VERSION
!error "Failed to determine PRODUCT_VERSION from meson.build. Pass /DPRODUCT_VERSION=<version> to makensis."
!endif
!define PRODUCT_PUBLISHER "DarkMatter Productions"
!define PRODUCT_WEB_SITE "www.darkmatter-quake.com"

; MUI 1.67 compatible ------
!include "MUI.nsh"

; MUI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"

; MUI Pages
!insertmacro MUI_PAGE_WELCOME
!define MUI_LICENSEPAGE_RADIOBUTTONS
!insertmacro MUI_PAGE_LICENSE "openQ4-game\EULA.Development Kit.rtf"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Language files
!insertmacro MUI_LANGUAGE "English"

; MUI end ------

Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "openQ4_${PRODUCT_VERSION}_SDK.exe"
InstallDir "C:\openQ4_SDK\"
ShowInstDetails show

Section "MainSection" SEC01
  SetOutPath "$INSTDIR"
  SetOverwrite ifnewer
  File /R "openQ4_SDK\*.*"
SectionEnd

Section -Post
SectionEnd

