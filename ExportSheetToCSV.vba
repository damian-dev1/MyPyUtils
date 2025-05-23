Option Explicit

Sub ExportSheetToCSV()
    Dim ws As Worksheet
    Dim rng As Range
    Dim csvFilePath As String
    Dim fileNum As Integer
    Dim rowNum As Long
    Dim colNum As Long
    Dim lastRow As Long
    Dim lastCol As Long
    Dim lineContent As String
    Dim cellValue As String
    Dim response As VbMsgBoxResult

    On Error GoTo ErrorHandler
    
    ' Select worksheet
    Set ws = ActiveSheet
    If ws Is Nothing Then
        MsgBox "No active sheet found!", vbCritical
        Exit Sub
    End If
    
    ' Confirm if user wants to continue
    response = MsgBox("Export active sheet '" & ws.Name & "' to CSV?", vbYesNo + vbQuestion, "Confirm Export")
    If response = vbNo Then Exit Sub
    
    ' Get range to export
    lastRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row
    lastCol = ws.Cells(1, ws.Columns.Count).End(xlToLeft).Column
    
    If lastRow < 1 Or lastCol < 1 Then
        MsgBox "Sheet is empty!", vbExclamation
        Exit Sub
    End If
    
    Set rng = ws.Range(ws.Cells(1, 1), ws.Cells(lastRow, lastCol))
    
    ' Prompt user for save location
    csvFilePath = Application.GetSaveAsFilename( _
        InitialFileName:=ws.Name & ".csv", _
        FileFilter:="CSV Files (*.csv), *.csv", _
        Title:="Save CSV As")
    
    If csvFilePath = "False" Then
        MsgBox "Export canceled.", vbInformation
        Exit Sub
    End If
    
    ' Create file
    fileNum = FreeFile
    Open csvFilePath For Output As #fileNum
    
    ' Loop through each row
    For rowNum = 1 To rng.Rows.Count
        lineContent = ""
        
        ' Build line for current row
        For colNum = 1 To rng.Columns.Count
            cellValue = rng.Cells(rowNum, colNum).Text
            
            ' Escape double quotes in cell values
            cellValue = Replace(cellValue, """", """""")
            
            ' Wrap in quotes if necessary
            If InStr(cellValue, ",") > 0 Or InStr(cellValue, """") > 0 Or InStr(cellValue, vbCrLf) > 0 Then
                cellValue = """" & cellValue & """"
            End If
            
            ' Append cell to line
            If colNum = 1 Then
                lineContent = cellValue
            Else
                lineContent = lineContent & "," & cellValue
            End If
        Next colNum
        
        ' Write line to file
        Print #fileNum, lineContent
    Next rowNum
    
    ' Close file
    Close #fileNum
    
    MsgBox "Export successful!" & vbCrLf & "File saved at: " & csvFilePath, vbInformation
    Exit Sub

ErrorHandler:
    If fileNum > 0 Then Close #fileNum
    MsgBox "An error occurred: " & Err.Description, vbCritical
End Sub
