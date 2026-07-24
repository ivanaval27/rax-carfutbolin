;====================================================
; RAX Carfutbolín — Instalador NSIS v2.4
; Wizard: Bienvenida → Licencia → Carpeta → Instalar → Finalizar
;====================================================

;----------------------------------------------------
; UNICODE
;----------------------------------------------------
Unicode true

;----------------------------------------------------
; DEFINES
;----------------------------------------------------
!define PRODUCT_NAME "RAX Carfutbolín"
!define PRODUCT_VERSION "2.4"
!define PRODUCT_PUBLISHER "RAX Corp"
!define PRODUCT_WEB_SITE "https://raxcorp.com"
!define PRODUCT_DIR_REGKEY "Software\Microsoft\Windows\CurrentVersion\App Paths\RAX Carfutbolin.exe"
!define PRODUCT_UNINST_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PRODUCT_NAME}"
!define PRODUCT_UNINST_ROOT_KEY HKLM
!define EXE_SOURCE "RAX Carfutbolin.exe"
!define SOUNDS_SOURCE "sounds"
!define ICO_SOURCE "rax_carfutbolin.ico"

;----------------------------------------------------
; INCLUDES
;----------------------------------------------------
!include "MUI2.nsh"
!include "FileFunc.nsh"
!include "x64.nsh"

;----------------------------------------------------
; PROPIEDADES
;----------------------------------------------------
Name "${PRODUCT_NAME} ${PRODUCT_VERSION}"
OutFile "RAX_Carfutbolin_Setup.exe"
InstallDir "$PROGRAMFILES64\${PRODUCT_NAME}"
InstallDirRegKey HKLM "${PRODUCT_DIR_REGKEY}" ""
RequestExecutionLevel admin
ShowInstDetails show
ShowUnInstDetails show
BrandingText "RAX Corp"

;----------------------------------------------------
; PAGINAS DEL WIZARD — Definir textos ANTES de las páginas
;----------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON "${ICO_SOURCE}"
!define MUI_UNICON "${ICO_SOURCE}"

; --- PÁGINA DE BIENVENIDA (texto plano, sin $\r$\n) ---
!define MUI_WELCOMEPAGE_TITLE "Bienvenido al instalador de RAX Carfutbolín"
!define MUI_WELCOMEPAGE_TEXT "Este asistente lo guiará en la instalacion de RAX Carfutbolin v${PRODUCT_VERSION}. Sistema de deteccion de goles para futbol de mesa con Arduino Nano. Se recomienda cerrar otras aplicaciones antes de continuar."

; --- PAGINA DE FINALIZACION ---
!define MUI_FINISHPAGE_TITLE "Instalacion completada"
!define MUI_FINISHPAGE_TEXT "RAX Carfutbolin se instalo correctamente. Se creo un acceso directo en el Escritorio y en el Menu Inicio."
!define MUI_FINISHPAGE_RUN "$INSTDIR\RAX Carfutbolin.exe"
!define MUI_FINISHPAGE_RUN_TEXT "Ejecutar RAX Carfutbolín ahora"
!define MUI_FINISHPAGE_NOREBOOT_SUPPORT

; Insertar páginas del wizard (5 páginas visibles)
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; Páginas desinstalador
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

;----------------------------------------------------
; IDIOMA
;----------------------------------------------------
!insertmacro MUI_LANGUAGE "Spanish"

;----------------------------------------------------
; SECCIÓN PRINCIPAL
;----------------------------------------------------
Section "RAX Carfutbolín" SEC01
    SetOutPath "$INSTDIR"

    ; Archivo principal
    File "${EXE_SOURCE}"

    ; Icono
    File "${ICO_SOURCE}"

    ; Carpeta sounds/ (si existe)
    IfFileExists "${SOUNDS_SOURCE}" 0 +3
        SetOutPath "$INSTDIR\sounds"
        File /nonfatal /r "${SOUNDS_SOURCE}\*.*"

    SetOutPath "$INSTDIR"

    ; Acceso directo en Escritorio
    CreateShortCut "$DESKTOP\RAX Carfutbolín.lnk" "$INSTDIR\RAX Carfutbolin.exe" "" "$INSTDIR\${ICO_SOURCE}"

    ; Acceso directo en Menú Inicio
    CreateDirectory "$SMPROGRAMS\RAX Carfutbolín"
    CreateShortCut "$SMPROGRAMS\RAX Carfutbolín\RAX Carfutbolín.lnk" "$INSTDIR\RAX Carfutbolin.exe" "" "$INSTDIR\${ICO_SOURCE}"
    CreateShortCut "$SMPROGRAMS\RAX Carfutbolín\Desinstalar RAX Carfutbolín.lnk" "$INSTDIR\uninst.exe"

    ; Registro
    WriteUninstaller "$INSTDIR\uninst.exe"
    WriteRegStr HKLM "${PRODUCT_DIR_REGKEY}" "" "$INSTDIR\RAX Carfutbolin.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayName" "${PRODUCT_NAME}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "UninstallString" "$INSTDIR\uninst.exe"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "DisplayVersion" "${PRODUCT_VERSION}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "Publisher" "${PRODUCT_PUBLISHER}"
    WriteRegStr ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}" "URLInfoAbout" "${PRODUCT_WEB_SITE}"
SectionEnd

;----------------------------------------------------
; DESINSTALACIÓN
;----------------------------------------------------
Section "Uninstall"
    Delete "$DESKTOP\RAX Carfutbolín.lnk"
    Delete "$SMPROGRAMS\RAX Carfutbolín\RAX Carfutbolín.lnk"
    Delete "$SMPROGRAMS\RAX Carfutbolín\Desinstalar RAX Carfutbolín.lnk"
    RMDir "$SMPROGRAMS\RAX Carfutbolín"

    Delete "$INSTDIR\RAX Carfutbolin.exe"
    Delete "$INSTDIR\${ICO_SOURCE}"
    Delete "$INSTDIR\carfutbolin.log"
    Delete "$INSTDIR\settings.json"
    RMDir /r "$INSTDIR\sounds"
    RMDir "$INSTDIR"

    DeleteRegKey ${PRODUCT_UNINST_ROOT_KEY} "${PRODUCT_UNINST_KEY}"
    DeleteRegKey HKLM "${PRODUCT_DIR_REGKEY}"
    SetAutoClose true
SectionEnd
