Sub ExportCSVAndPDF()
    ' This is the main subroutine that calls the individual functions
    ' to export the current sheet as a CSV and PDF file.
    
    Dim currentSheet As Worksheet
    Set currentSheet = ActiveSheet
    
    ' Declare variables for file paths
    Dim csvFilePath As String
    Dim pdfFilePath As String
    
    ' Get the file paths from the user
    csvFilePath = GetCSVFilePath()
    pdfFilePath = GetPDFFilePath()

    ' Export the sheet as CSV
    If csvFilePath <> "" Then
        ExportSheetAsCSV currentSheet, csvFilePath
    Else
        MsgBox "CSV export canceled"
    End If
    
    ' Export the sheet as PDF
    If pdfFilePath <> "" Then
        ExportSheetAsPDF currentSheet, pdfFilePath
    Else
        MsgBox "PDF export canceled"
    End If
    
    MsgBox "Export process completed."
End Sub

' Function to prompt the user for the CSV file path
Function GetCSVFilePath() As String
    Dim fileDialog As FileDialog
    Set fileDialog = Application.FileDialog(msoFileDialogSaveAs)
    
    ' Set default extension to .csv
    fileDialog.FilterIndex = 6
    fileDialog.DefaultFilePath = Application.DefaultFilePath & "\Sheet.csv"
    
    ' Show the file dialog
    If fileDialog.Show = -1 Then
        GetCSVFilePath = fileDialog.SelectedItems(1)
    Else
        GetCSVFilePath = ""
    End If
End Function

' Function to prompt the user for the PDF file path
Function GetPDFFilePath() As String
    Dim fileDialog As FileDialog
    Set fileDialog = Application.FileDialog(msoFileDialogSaveAs)
    
    ' Set default extension to .pdf
    fileDialog.FilterIndex = 15
    fileDialog.DefaultFilePath = Application.DefaultFilePath & "\Sheet.pdf"
    
    ' Show the file dialog
    If fileDialog.Show = -1 Then
        GetPDFFilePath = fileDialog.SelectedItems(1)
    Else
        GetPDFFilePath = ""
    End If
End Function

' Procedure to export the current sheet as a CSV file
Sub ExportSheetAsCSV(ByVal ws As Worksheet, ByVal filePath As String)
    ' Save the current sheet as a CSV file at the given file path
    On Error GoTo ErrorHandler
    
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    ws.SaveAs fileName:=filePath, FileFormat:=xlCSV
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    
    MsgBox "CSV Exported Successfully to " & filePath
    Exit Sub

ErrorHandler:
    MsgBox "An error occurred while exporting the sheet to CSV: " & Err.Description
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
End Sub

' Procedure to export the current sheet as a PDF file
Sub ExportSheetAsPDF(ByVal ws As Worksheet, ByVal filePath As String)
    ' Export the current sheet as a PDF file at the given file path
    On Error GoTo ErrorHandler
    
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    
    ' Set PDF print options
    ws.PageSetup.Orientation = xlPortrait
    ws.PageSetup.PaperSize = xlPaperA4
    ws.PageSetup.FitToPagesWide = 1
    ws.PageSetup.FitToPagesTall = False
    
    ' Export to PDF
    ws.ExportAsFixedFormat Type:=xlTypePDF, Filename:=filePath, Quality:=xlQualityStandard
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    
    MsgBox "PDF Exported Successfully to " & filePath
    Exit Sub

ErrorHandler:
    MsgBox "An error occurred while exporting the sheet to PDF: " & Err.Description
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
End Sub

' Function to get the current date and time as a string (for unique filenames)
Function GetDateTimeString() As String
    Dim currentDateTime As String
    currentDateTime = Format(Now, "yyyy-mm-dd_hhmmss")
    GetDateTimeString = currentDateTime
End Function

' Function to log the export activities to a text file for reference
Sub LogExportActivity(ByVal action As String, ByVal filePath As String)
    Dim logFilePath As String
    logFilePath = Application.DefaultFilePath & "\ExportLog.txt"
    
    ' Open the log file in append mode
    Dim logFile As Integer
    logFile = FreeFile
    Open logFilePath For Append As logFile
    
    ' Write the action and file path to the log file
    Print #logFile, Format(Now, "yyyy-mm-dd hh:mm:ss") & " - " & action & " to " & filePath
    
    ' Close the file
    Close logFile
End Sub

' Function to check if a file already exists
Function FileExists(ByVal filePath As String) As Boolean
    On Error Resume Next
    FileExists = (Dir(filePath) <> "")
    On Error GoTo 0
End Function

' Subroutine to preview the export settings
Sub PreviewExportSettings()
    ' Display the settings for the export operation
    MsgBox "The current settings for the export are as follows:" & vbCrLf & _
           "CSV File Format: .csv" & vbCrLf & _
           "PDF File Format: .pdf" & vbCrLf & _
           "Orientation: Portrait" & vbCrLf & _
           "Paper Size: A4" & vbCrLf & _
           "Fit to Width: 1 page"
End Sub

' Function to format the CSV data for special characters handling (like quotes, commas)
Function FormatCSVData(ByVal cellValue As String) As String
    ' Check if the value contains a comma or quote
    If InStr(cellValue, ",") > 0 Or InStr(cellValue, """") > 0 Then
        ' Escape the quotes by doubling them and wrap the data in quotes
        cellValue = """" & Replace(cellValue, """", """""") & """"
    End If
    FormatCSVData = cellValue
End Function
