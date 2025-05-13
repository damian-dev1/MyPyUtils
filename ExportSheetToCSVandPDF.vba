Option Explicit

' === MAIN ENTRY POINT ===
Sub ExportSheetToCSVandPDF()
    Dim currentSheet As Worksheet
    Set currentSheet = ActiveSheet
    
    Dim exportFolder As String
    Dim baseFileName As String
    Dim csvFilePath As String
    Dim pdfFilePath As String
    
    ' Ensure Exports folder exists
    exportFolder = ThisWorkbook.Path & "\Exports"
    CreateExportsFolder exportFolder
    
    ' Generate Base File Name
    baseFileName = "Sheet_" & GetDateTimeString()
    
    ' Build full paths
    csvFilePath = exportFolder & "\" & EnsureExtension(baseFileName, "csv")
    pdfFilePath = exportFolder & "\" & EnsureExtension(baseFileName, "pdf")
    
    ' Export operations
    ExportSheetAsCSV currentSheet, csvFilePath
    ExportSheetAsPDF currentSheet, pdfFilePath
    
    ' Log the export
    LogExportActivity "CSV Export", csvFilePath
    LogExportActivity "PDF Export", pdfFilePath
    
    ' Final confirmation
    MsgBox "✅ Export completed successfully!" & vbCrLf & vbCrLf & _
           "📄 CSV: " & csvFilePath & vbCrLf & _
           "📄 PDF: " & pdfFilePath, vbInformation, "Export Completed"
End Sub

' === UTILITY: Create Exports folder if missing ===
Sub CreateExportsFolder(ByVal folderPath As String)
    If Dir(folderPath, vbDirectory) = "" Then
        MkDir folderPath
    End If
End Sub

' === UTILITY: Export active sheet to CSV ===
Sub ExportSheetAsCSV(ByVal ws As Worksheet, ByVal filePath As String)
    On Error GoTo ErrorHandler
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    
    ws.Copy
    ActiveWorkbook.SaveAs Filename:=filePath, FileFormat:=xlCSV
    ActiveWorkbook.Close SaveChanges:=False
    
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    Exit Sub
    
ErrorHandler:
    MsgBox "❌ Error exporting CSV: " & Err.Description, vbCritical
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
End Sub

' === UTILITY: Export active sheet to PDF ===
Sub ExportSheetAsPDF(ByVal ws As Worksheet, ByVal filePath As String)
    On Error GoTo ErrorHandler
    Application.ScreenUpdating = False
    Application.DisplayAlerts = False
    
    With ws.PageSetup
        .Orientation = xlPortrait
        .PaperSize = xlPaperA4
        .FitToPagesWide = 1
        .FitToPagesTall = False
    End With
    
    ws.ExportAsFixedFormat Type:=xlTypePDF, Filename:=filePath, Quality:=xlQualityStandard
    
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
    Exit Sub
    
ErrorHandler:
    MsgBox "❌ Error exporting PDF: " & Err.Description, vbCritical
    Application.DisplayAlerts = True
    Application.ScreenUpdating = True
End Sub

' === UTILITY: Log actions to ExportLog.txt ===
Sub LogExportActivity(ByVal actionType As String, ByVal filePath As String)
    Dim logFilePath As String
    logFilePath = ThisWorkbook.Path & "\Exports\ExportLog.txt"
    
    Dim logFile As Integer
    logFile = FreeFile
    
    Open logFilePath For Append As logFile
    Print #logFile, Format(Now, "yyyy-mm-dd hh:mm:ss") & " - " & actionType & " - " & filePath
    Close logFile
End Sub

' === UTILITY: Get current date-time string ===
Function GetDateTimeString() As String
    GetDateTimeString = Format(Now, "yyyy-mm-dd_hhmmss")
End Function

' === UTILITY: Ensure correct extension ===
Function EnsureExtension(ByVal baseName As String, ByVal extension As String) As String
    ' Remove any existing extension
    If InStrRev(baseName, ".") > 0 Then
        baseName = Left(baseName, InStrRev(baseName, ".") - 1)
    End If
    EnsureExtension = baseName & "." & extension
End Function
