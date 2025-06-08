Sub ApplyDynamicDataValidation()

    Dim wsValidation As Worksheet, wsDashboard As Worksheet
    Dim lastRowDash As Long, lastCol As Long, i As Long
    Dim header As String, namedRange As String
    Dim validationCol As Range, validationRange As Range
    Dim cell As Range

    Set wsValidation = ThisWorkbook.Sheets("DataValidation")
    Set wsDashboard = ThisWorkbook.Sheets("Dashboard")

    ' Get the last column in DataValidation
    lastCol = wsValidation.Cells(1, wsValidation.Columns.Count).End(xlToLeft).Column

    ' Create named ranges dynamically
    For i = 1 To lastCol
        header = wsValidation.Cells(1, i).Value
        If header <> "" Then
            namedRange = header & "List"
            ' Define dynamic named range (skip blank rows)
            ThisWorkbook.Names.Add Name:=namedRange, _
                RefersToR1C1:="=OFFSET(DataValidation!R2C" & i & ",0,0,COUNTA(DataValidation!C" & i & ")-1,1)"
        End If
    Next i

    ' Get the last used row in Dashboard
    lastRowDash = wsDashboard.Cells(wsDashboard.Rows.Count, 1).End(xlUp).Row

    ' Apply data validation
    For i = 1 To lastCol
        header = wsDashboard.Cells(1, i).Value
        namedRange = header & "List"

        ' Confirm named range exists
        If Evaluate("ISREF(" & namedRange & ")") Then
            Set validationCol = wsDashboard.Range(wsDashboard.Cells(2, i), wsDashboard.Cells(lastRowDash, i))
            With validationCol.Validation
                .Delete
                .Add Type:=xlValidateList, AlertStyle:=xlValidAlertStop, _
                    Operator:=xlBetween, Formula1:="=" & namedRange
                .IgnoreBlank = True
                .InCellDropdown = True
                .InputTitle = ""
                .ErrorTitle = "Invalid Entry"
                .InputMessage = ""
                .ErrorMessage = "Please select a value from the dropdown list."
                .ShowInput = True
                .ShowError = True
            End With
        End If
    Next i

    MsgBox "Dynamic validation applied to Dashboard sheet.", vbInformation

End Sub
