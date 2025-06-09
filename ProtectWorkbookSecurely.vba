Option Explicit

Sub ProtectWorkbookSecurely()
    Dim ws As Worksheet
    Dim wb As Workbook
    Dim sheetPassword As String
    Dim structurePassword As String
    Dim rng As Range

    On Error GoTo HandleError
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False

    ' === Define passwords ===
    sheetPassword = "ShtP@ss2025"         ' Change as needed
    structurePassword = "WbkP@ss2025"     ' Change as needed

    Set wb = ThisWorkbook

    ' === Protect workbook structure ===
    If Not wb.ProtectStructure Then
        wb.Protect Password:=structurePassword, Structure:=True, Windows:=False
    End If

    ' === Protect each sheet ===
    For Each ws In wb.Worksheets
        With ws
            ' Optional: unlock all cells first
            .Cells.Locked = False
            .Cells.FormulaHidden = False
            
            ' Lock only input cells (example: leave Column A unlocked)
            Set rng = .UsedRange
            rng.Cells.Locked = True
            rng.Cells.FormulaHidden = True
            
            ' Example: unlock specific input cells
            On Error Resume Next
            .Range("A2:A100").Locked = False
            On Error GoTo 0

            ' Now apply protection
            .Protect Password:=sheetPassword, _
                     DrawingObjects:=True, _
                     Contents:=True, _
                     Scenarios:=True, _
                     AllowFormattingCells:=False, _
                     AllowFormattingColumns:=False, _
                     AllowFormattingRows:=False, _
                     AllowInsertingColumns:=False, _
                     AllowInsertingRows:=False, _
                     AllowDeletingColumns:=False, _
                     AllowDeletingRows:=False, _
                     AllowSorting:=False, _
                     AllowFiltering:=True, _
                     AllowUsingPivotTables:=False
        End With
    Next ws

    MsgBox "Workbook and sheets protected successfully.", vbInformation
    Application.ScreenUpdating = True
    Exit Sub

HandleError:
    MsgBox "Protection failed: " & Err.Description, vbCritical
    Application.ScreenUpdating = True
End Sub
