$pdfPath = 'c:\Users\r.petniunas\Downloads\AI\rpetni-AE.CAP.1.1\Internal rules\org structure.pdf'

try {
    # Read PDF as binary
    $bytes = [System.IO.File]::ReadAllBytes($pdfPath)
    
    # Convert to string and extract readable text
    $text = [System.Text.Encoding]::ASCII.GetString($bytes)
    
    # Filter out binary data and keep readable characters
    $cleaned = $text -replace '[^\x20-\x7E\n\r\t]', ''
    
    # Output the cleaned text
    Write-Output $cleaned
}
catch {
    Write-Error "Error reading PDF: $_"
}
