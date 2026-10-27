# 글별 OG 이미지. 1200x630, Malgun Gothic. 로컬(Windows)에서만 돈다 — Actions 러너에는 한글 폰트가 없다.
param(
  [Parameter(Mandatory)][string]$Title,
  [Parameter(Mandatory)][string]$Out,
  [string]$Topic = "",
  [string]$Kind = "",
  [string]$Color = "#3b5bdb"
)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Drawing

$w = 1200; $h = 630
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = 'AntiAlias'
$g.TextRenderingHint = 'AntiAliasGridFit'

$accent = [System.Drawing.ColorTranslator]::FromHtml($Color)
$ink = [System.Drawing.ColorTranslator]::FromHtml('#1f2328')
$muted = [System.Drawing.ColorTranslator]::FromHtml('#6b7280')

# 바탕: 크림 + 오른쪽 아래 연한 주제색 원
$g.Clear([System.Drawing.ColorTranslator]::FromHtml('#fffcf7'))
$soft = [System.Drawing.Color]::FromArgb(28, $accent.R, $accent.G, $accent.B)
$g.FillEllipse((New-Object System.Drawing.SolidBrush $soft), 760, 300, 700, 700)
# 왼쪽 색 띠
$g.FillRectangle((New-Object System.Drawing.SolidBrush $accent), 0, 0, 18, $h)

$fmt = [System.Drawing.StringFormat]::GenericTypographic.Clone()
$fmt.Trimming = 'EllipsisWord'
$fmt.FormatFlags = [System.Drawing.StringFormatFlags]::LineLimit

# 주제 · 종류
$label = $Topic
if ($Kind) { if ($label) { $label = "$label  ·  $Kind" } else { $label = $Kind } }
if ($label) {
  $f = New-Object System.Drawing.Font('Malgun Gothic', 24, [System.Drawing.FontStyle]::Bold)
  $g.DrawString($label, $f, (New-Object System.Drawing.SolidBrush $accent), 90, 88, $fmt)
}

# 제목: 길이에 따라 크기 조절, 최대 3줄
$size = 60
if ($Title.Length -gt 28) { $size = 52 }
if ($Title.Length -gt 44) { $size = 44 }
$f = New-Object System.Drawing.Font('Malgun Gothic', $size, [System.Drawing.FontStyle]::Bold)
# 단어 단위 줄바꿈 (GDI+ 는 한글을 글자 단위로 끊는다). 최대 3줄, 넘치면 말줄임.
$maxW = 1030
$lines = New-Object System.Collections.Generic.List[string]
$cur = ''
foreach ($word in ($Title -split ' ')) {
  $try = if ($cur) { "$cur $word" } else { $word }
  if ($g.MeasureString($try, $f, 10000, $fmt).Width -le $maxW) { $cur = $try }
  else {
    if ($cur) { $lines.Add($cur) }
    $cur = $word
  }
}
if ($cur) { $lines.Add($cur) }
if ($lines.Count -gt 3) {
  $lines = $lines.GetRange(0, 3)
  $last = $lines[2]
  while ($last.Length -gt 1 -and $g.MeasureString("$last…", $f, 10000, $fmt).Width -gt $maxW) { $last = $last.Substring(0, $last.Length - 1) }
  $lines[2] = "$last…"
}
$lineH = $f.GetHeight($g)
$y = 150
foreach ($line in $lines) {
  $g.DrawString($line, $f, (New-Object System.Drawing.SolidBrush $ink), 90, $y, $fmt)
  $y += $lineH
}

# 아래: 사이트 이름 · 주소
$f = New-Object System.Drawing.Font('Malgun Gothic', 30, [System.Drawing.FontStyle]::Bold)
$g.DrawString('AI하고', $f, (New-Object System.Drawing.SolidBrush $ink), 90, 540, $fmt)
$nameW = $g.MeasureString('AI하고', $f, 400, $fmt).Width
$f2 = New-Object System.Drawing.Font('Malgun Gothic', 24)
$g.DrawString('aihago.com', $f2, (New-Object System.Drawing.SolidBrush $muted), (90 + $nameW + 22), 550, $fmt)

$dir = Split-Path $Out -Parent
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose(); $bmp.Dispose()
Write-Output $Out
