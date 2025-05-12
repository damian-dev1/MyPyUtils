Option Explicit

Sub ResetTableOrSheet()
    Dim ws As Worksheet
    Dim tbl As ListObject
    Dim rng As Range
    Dim targetRange As Range
    Dim cell As Range
    Dim visibleRange As Range
    Dim isInTable As Boolean
    Dim tblName As String
    
    On Error GoTo ErrHandler
    
    Set ws = ActiveSheet
    If ws Is Nothing Then Exit Sub
    
    ' Check if selection is inside a Table
    On Error Resume Next
    tblName = Selection.ListObject.Name
    On Error GoTo 0
    
    If Len(tblName) > 0 Then
        ' Clear the selected Table
        Set tbl = ws.ListObjects(tblName)
        If Not tbl Is Nothing Then
            If Not tbl.DataBodyRange Is Nothing Then
                ' Only clear visible cells inside the table
                Set visibleRange = GetVisibleRange(tbl.DataBodyRange)
                If Not visibleRange Is Nothing Then
                    visibleRange.ClearContents
                End If
            End If
        End If
    Else
        ' No table selected - Clear the entire sheet (visible cells only)
        Set targetRange = ws.UsedRange.SpecialCells(xlCellTypeVisible)
        If Not targetRange Is Nothing Then
            targetRange.ClearContents
        End If
    End If

    Exit Sub
    
ErrHandler:
    MsgBox "An error occurred: " & Err.Description, vbExclamation
End Sub

' Helper: Get only visible cells in a range
Function GetVisibleRange(rng As Range) As Range
    Dim cell As Range
    Dim tempRange As Range
    For Each cell In rng
        If Not cell.EntireRow.Hidden And Not cell.EntireColumn.Hidden Then
            If tempRange Is Nothing Then
                Set tempRange = cell
            Else
                Set tempRange = Union(tempRange, cell)
            End If
        End If
    Next cell
    Set GetVisibleRange = tempRange
End Function
