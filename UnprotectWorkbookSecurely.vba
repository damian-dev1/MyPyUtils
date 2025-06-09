Option Explicit

Sub UnprotectWorkbookSecurely()
    Dim ws As Worksheet
    Dim wb As Workbook
    Dim sheetPassword As String
    Dim structurePassword As String

    On Error GoTo HandleError
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False

    ' === Define passwords ===
    sheetPassword = "ShtP@ss2025"         ' Must match what was used in protection
    structurePassword = "WbkP@ss2025"     ' Must match what was used in protection

    Set wb = ThisWorkbook

    ' === Unprotect workbook structure ===
    If wb.ProtectStructure Then
        wb.Unprotect Password:=structurePassword
    End If

    ' === Unprotect and unlock each sheet ===
    For Each ws In wb.Worksheets
        With ws
            ' Unprotect the sheet
            .Unprotect Password:=sheetPassword

            ' Unlock all cells and unhide formulas
            .Cells.Locked = False
            .Cells.FormulaHidden = False
        End With
    Next ws

    MsgBox "Workbook and sheets unprotected successfully.", vbInformation
    Application.ScreenUpdating = True
    Exit Sub

HandleError:
    MsgBox "Unprotection failed: " & Err.Description, vbCritical
    Application.ScreenUpdating = True
End Sub
