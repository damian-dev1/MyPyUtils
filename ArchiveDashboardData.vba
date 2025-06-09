Option Explicit

Sub ArchiveDashboardData()
    Dim wsDashboard As Worksheet, wsArchive As Worksheet, wsLogs As Worksheet
    Dim lastRowDash As Long, lastRowArch As Long, lastRowLog As Long
    Dim rngData As Range, rngDest As Range
    Dim timestamp As String
    Dim i As Long, j As Long
    Dim success As Boolean
    Dim msg As String

    On Error GoTo HandleError

    ' Initialize
    Application.ScreenUpdating = False
    timestamp = Format(Now, "yyyy-mm-dd HH:MM:SS")
    success = False

    ' Set or create Dashboard sheet
    Set wsDashboard = ThisWorkbook.Sheets("Dashboard")

    ' Create Archive sheet if not exist
    On Error Resume Next
    Set wsArchive = ThisWorkbook.Sheets("Archive")
    If wsArchive Is Nothing Then
        Set wsArchive = ThisWorkbook.Sheets.Add(After:=Sheets(Sheets.Count))
        wsArchive.Name = "Archive"
    End If
    On Error GoTo 0

    ' Create Logs sheet if not exist
    On Error Resume Next
    Set wsLogs = ThisWorkbook.Sheets("Logs")
    If wsLogs Is Nothing Then
        Set wsLogs = ThisWorkbook.Sheets.Add(After:=Sheets(Sheets.Count))
        wsLogs.Name = "Logs"
        wsLogs.Range("A1:C1").Value = Array("Timestamp", "Status", "Details")
    End If
    On Error GoTo 0

    ' Find last data row on Dashboard
    lastRowDash = wsDashboard.Cells(wsDashboard.Rows.Count, 1).End(xlUp).Row
    If lastRowDash <= 1 Then
        msg = "No data to archive."
        GoTo LogAndExit
    End If

    ' Define range to copy (excluding header)
    Set rngData = wsDashboard.Range("A2", wsDashboard.Cells(lastRowDash, wsDashboard.Cells(1, wsDashboard.Columns.Count).End(xlToLeft).Column))

    ' Prepare Archive header if not exists
    If wsArchive.Cells(1, 1).Value = "" Then
        wsArchive.Cells(1, 1).Value = "Date Archived"
        rngData.Offset(-1, 0).Copy wsArchive.Cells(1, 2) ' Copy header from Dashboard
    End If

    ' Find last row in Archive
    lastRowArch = wsArchive.Cells(wsArchive.Rows.Count, 1).End(xlUp).Row + 1

    ' Copy each row with timestamp prepended
    For i = 1 To rngData.Rows.Count
        wsArchive.Cells(lastRowArch + i - 1, 1).Value = timestamp
        For j = 1 To rngData.Columns.Count
            wsArchive.Cells(lastRowArch + i - 1, j + 1).Value = rngData.Cells(i, j).Value
        Next j
    Next i

    ' Clear Dashboard data (keep header)
    wsDashboard.Range("A2:" & wsDashboard.Cells(wsDashboard.Rows.Count, 1).End(xlUp).Address).EntireRow.ClearContents

    success = True
    msg = rngData.Rows.Count & " rows archived from Dashboard to Archive."

LogAndExit:
    ' Write to Logs
    lastRowLog = wsLogs.Cells(wsLogs.Rows.Count, 1).End(xlUp).Row + 1
    wsLogs.Cells(lastRowLog, 1).Value = timestamp
    wsLogs.Cells(lastRowLog, 2).Value = IIf(success, "Success", "Skipped")
    wsLogs.Cells(lastRowLog, 3).Value = msg

    Application.ScreenUpdating = True
    Exit Sub

HandleError:
    msg = "Error: " & Err.Description
    Resume LogAndExit
End Sub
