param(
    [string]$OutputDir = (Join-Path $PSScriptRoot "assets\brand")
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

function New-RoundedRectPath {
    param(
        [System.Drawing.Rectangle]$Rect,
        [int]$Radius
    )

    $path = New-Object System.Drawing.Drawing2D.GraphicsPath
    $diameter = $Radius * 2
    $arcRect = New-Object System.Drawing.Rectangle $Rect.X, $Rect.Y, $diameter, $diameter

    $path.AddArc($arcRect, 180, 90)
    $arcRect.X = $Rect.Right - $diameter
    $path.AddArc($arcRect, 270, 90)
    $arcRect.Y = $Rect.Bottom - $diameter
    $path.AddArc($arcRect, 0, 90)
    $arcRect.X = $Rect.X
    $path.AddArc($arcRect, 90, 90)
    $path.CloseFigure()

    return $path
}

function Save-Png {
    param(
        [System.Drawing.Bitmap]$Bitmap,
        [string]$Path
    )

    $Bitmap.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
}

function Save-Icon {
    param(
        [System.Drawing.Bitmap]$Bitmap,
        [string]$Path
    )

    $icon = [System.Drawing.Icon]::FromHandle($Bitmap.GetHicon())
    try {
        $stream = [System.IO.File]::Create($Path)
        try {
            $icon.Save($stream)
        } finally {
            $stream.Dispose()
        }
    } finally {
        $icon.Dispose()
    }
}

function New-BaseBitmap {
    param(
        [int]$Width,
        [int]$Height
    )

    return New-Object System.Drawing.Bitmap $Width, $Height
}

function Draw-Grid {
    param(
        [System.Drawing.Graphics]$Graphics,
        [int]$Width,
        [int]$Height,
        [int]$Spacing,
        [System.Drawing.Color]$Color
    )

    $pen = New-Object System.Drawing.Pen $Color, 1
    try {
        for ($x = 0; $x -le $Width; $x += $Spacing) {
            $Graphics.DrawLine($pen, $x, 0, $x, $Height)
        }
        for ($y = 0; $y -le $Height; $y += $Spacing) {
            $Graphics.DrawLine($pen, 0, $y, $Width, $y)
        }
    } finally {
        $pen.Dispose()
    }
}

function Draw-Candles {
    param(
        [System.Drawing.Graphics]$Graphics,
        [int]$BaseX,
        [int]$BaseY,
        [int]$Scale
    )

    $wickUp = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(185, 120, 255, 190)), ($Scale / 7)
    $wickDown = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(180, 95, 205, 255)), ($Scale / 7)
    $bull = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(230, 76, 201, 128))
    $bear = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(230, 80, 150, 255))
    $glow = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(40, 98, 255, 200))
    try {
        $candles = @(
            @{ X = 0; H = 140; W = 30; Body = 48; Bull = $true  },
            @{ X = 62; H = 180; W = 34; Body = 58; Bull = $false },
            @{ X = 130; H = 110; W = 30; Body = 44; Bull = $true  },
            @{ X = 196; H = 155; W = 34; Body = 62; Bull = $true  },
            @{ X = 268; H = 95;  W = 28; Body = 40; Bull = $false }
        )

        foreach ($c in $candles) {
            $x = $BaseX + $c.X
            $top = $BaseY - $c.H
            $bodyTop = $BaseY - [Math]::Max($c.Body, 24)
            $bodyBottom = $BaseY - 10
            $bodyLeft = $x - ($c.W / 2)

            $Graphics.FillEllipse($glow, $x - 18, $top - 18, 36, 36)
            $pen = if ($c.Bull) { $wickUp } else { $wickDown }
            $Graphics.DrawLine($pen, $x, $top, $x, $BaseY - 6)

            $brush = if ($c.Bull) { $bull } else { $bear }
            $rect = New-Object System.Drawing.Rectangle ([int]$bodyLeft), ([int]$bodyTop), ([int]$c.W), ([int]($bodyBottom - $bodyTop))
            $Graphics.FillRectangle($brush, $rect)
            $border = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(90, 255, 255, 255)), 1
            try {
                $Graphics.DrawRectangle($border, $rect)
            } finally {
                $border.Dispose()
            }
        }
    } finally {
        $wickUp.Dispose()
        $wickDown.Dispose()
        $bull.Dispose()
        $bear.Dispose()
        $glow.Dispose()
    }
}

function Draw-LineGraph {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.Point[]]$Points,
        [System.Drawing.Color]$Color,
        [int]$Thickness
    )

    $pen = New-Object System.Drawing.Pen $Color, $Thickness
    $pen.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
    try {
        $Graphics.DrawLines($pen, $Points)
    } finally {
        $pen.Dispose()
    }
}

function New-Background {
    param(
        [int]$Width,
        [int]$Height,
        [string]$Path
    )

    $bmp = New-BaseBitmap -Width $Width -Height $Height
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

    try {
        $bgRect = New-Object System.Drawing.Rectangle 0, 0, $Width, $Height
        $bgBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
            $bgRect,
            [System.Drawing.Color]::FromArgb(255, 10, 17, 30),
            [System.Drawing.Color]::FromArgb(255, 12, 42, 65),
            35
        )
        try {
            $blend = New-Object System.Drawing.Drawing2D.ColorBlend
            $blend.Positions = @(0.0, 0.45, 1.0)
            $blend.Colors = @(
                [System.Drawing.Color]::FromArgb(255, 7, 14, 24),
                [System.Drawing.Color]::FromArgb(255, 15, 31, 54),
                [System.Drawing.Color]::FromArgb(255, 7, 21, 33)
            )
            $bgBrush.InterpolationColors = $blend
            $g.FillRectangle($bgBrush, $bgRect)
        } finally {
            $bgBrush.Dispose()
        }

        $upperGlow = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(18, 110, 255, 205))
        $upperGlow2 = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(14, 120, 150, 255))
        try {
            $g.FillEllipse($upperGlow, ([int]($Width * 0.03)), ([int]($Height * 0.06)), ([int]($Width * 0.28)), ([int]($Height * 0.20)))
            $g.FillEllipse($upperGlow2, ([int]($Width * 0.21)), ([int]($Height * 0.11)), ([int]($Width * 0.16)), ([int]($Height * 0.12)))
        } finally {
            $upperGlow.Dispose()
            $upperGlow2.Dispose()
        }

        Draw-Grid -Graphics $g -Width $Width -Height $Height -Spacing ([Math]::Max(75, [int]($Width / 24))) -Color ([System.Drawing.Color]::FromArgb(20, 150, 200, 255))

        $pathBrush = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(36, 0, 0, 0))
        try {
            $trackY = [int]($Height * 0.65)
            $trackPoints = New-Object System.Collections.Generic.List[System.Drawing.Point]
            $trackPoints.Add((New-Object System.Drawing.Point ([int]($Width * 0.05)), ([int]($Height * 0.78))))
            $trackPoints.Add((New-Object System.Drawing.Point ([int]($Width * 0.16)), ([int]($Height * 0.74))))
            $trackPoints.Add((New-Object System.Drawing.Point ([int]($Width * 0.24)), ([int]($Height * 0.58))))
            $trackPoints.Add((New-Object System.Drawing.Point ([int]($Width * 0.35)), ([int]($Height * 0.62))))
            $trackPoints.Add((New-Object System.Drawing.Point ([int]($Width * 0.47)), ([int]($Height * 0.50))))
            $trackPoints.Add((New-Object System.Drawing.Point ([int]($Width * 0.58)), ([int]($Height * 0.56))))
            $trackPoints.Add((New-Object System.Drawing.Point ([int]($Width * 0.69)), ([int]($Height * 0.41))))
            $trackPoints.Add((New-Object System.Drawing.Point ([int]($Width * 0.80)), ([int]($Height * 0.46))))
            $trackPoints.Add((New-Object System.Drawing.Point ([int]($Width * 0.92)), ([int]($Height * 0.31))))

            $softLine = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(55, 69, 255, 195)), ([Math]::Max(6, [int]($Height / 250)))
            $softLine.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
            try {
                $g.DrawLines($softLine, $trackPoints.ToArray())
            } finally {
                $softLine.Dispose()
            }

            $hardLine = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(255, 120, 255, 190)), ([Math]::Max(3, [int]($Height / 420)))
            $hardLine.LineJoin = [System.Drawing.Drawing2D.LineJoin]::Round
            try {
                $g.DrawLines($hardLine, $trackPoints.ToArray())
            } finally {
                $hardLine.Dispose()
            }
        } finally {
            $pathBrush.Dispose()
        }

        $bottomBase = [int]($Height * 0.78)
        Draw-Candles -Graphics $g -BaseX ([int]($Width * 0.22)) -BaseY $bottomBase -Scale ([Math]::Max(1, [int]($Height / 1080)))

        $frameBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
            $bgRect,
            [System.Drawing.Color]::FromArgb(0, 255, 255, 255),
            [System.Drawing.Color]::FromArgb(55, 80, 145, 255),
            80
        )
        try {
            $g.FillRectangle($frameBrush, 0, [int]($Height * 0.87), $Width, [int]($Height * 0.13))
        } finally {
            $frameBrush.Dispose()
        }

        $highlights = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(45, 255, 255, 255)), 2
        try {
            $g.DrawEllipse($highlights, ([int]($Width * 0.67)), ([int]($Height * 0.18)), ([int]($Width * 0.20)), ([int]($Height * 0.20)))
            $g.DrawEllipse($highlights, ([int]($Width * 0.70)), ([int]($Height * 0.22)), ([int]($Width * 0.10)), ([int]($Height * 0.10)))
        } finally {
            $highlights.Dispose()
        }

        Save-Png -Bitmap $bmp -Path $Path
    } finally {
        $g.Dispose()
        $bmp.Dispose()
    }
}

function New-IconArt {
    param(
        [int]$Size,
        [string]$PngPath,
        [string]$IcoPath
    )

    $bmp = New-BaseBitmap -Width $Size -Height $Size
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality
    $g.CompositingQuality = [System.Drawing.Drawing2D.CompositingQuality]::HighQuality
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality

    try {
        $fullRect = New-Object System.Drawing.Rectangle 0, 0, $Size, $Size
        $bgPath = New-RoundedRectPath -Rect (New-Object System.Drawing.Rectangle 8, 8, ($Size - 16), ($Size - 16)) -Radius 48
        $bgBrush = New-Object System.Drawing.Drawing2D.LinearGradientBrush(
            $fullRect,
            [System.Drawing.Color]::FromArgb(255, 11, 18, 33),
            [System.Drawing.Color]::FromArgb(255, 12, 57, 78),
            45
        )
        try {
            $g.FillPath($bgBrush, $bgPath)
        } finally {
            $bgBrush.Dispose()
        }

        $innerGlow = New-Object System.Drawing.SolidBrush ([System.Drawing.Color]::FromArgb(28, 100, 255, 190))
        try {
            $g.FillEllipse($innerGlow, 40, 36, 176, 176)
        } finally {
            $innerGlow.Dispose()
        }

        $frame = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(100, 255, 255, 255)), 2
        try {
            $g.DrawPath($frame, $bgPath)
        } finally {
            $frame.Dispose()
        }

        Draw-Grid -Graphics $g -Width $Size -Height $Size -Spacing 32 -Color ([System.Drawing.Color]::FromArgb(18, 160, 220, 255))

        Draw-Candles -Graphics $g -BaseX 54 -BaseY 178 -Scale 1

        $pathPoints = @(
            (New-Object System.Drawing.Point 38, 184),
            (New-Object System.Drawing.Point 64, 170),
            (New-Object System.Drawing.Point 84, 132),
            (New-Object System.Drawing.Point 114, 143),
            (New-Object System.Drawing.Point 140, 104),
            (New-Object System.Drawing.Point 166, 118),
            (New-Object System.Drawing.Point 194, 84),
            (New-Object System.Drawing.Point 216, 94)
        )
        Draw-LineGraph -Graphics $g -Points $pathPoints -Color ([System.Drawing.Color]::FromArgb(255, 119, 255, 188)) -Thickness 5
        Draw-LineGraph -Graphics $g -Points $pathPoints -Color ([System.Drawing.Color]::FromArgb(120, 255, 255, 255)) -Thickness 2

        $orbit = New-Object System.Drawing.Pen ([System.Drawing.Color]::FromArgb(80, 255, 255, 255)), 2
        try {
            $g.DrawEllipse($orbit, 28, 28, 200, 200)
        } finally {
            $orbit.Dispose()
        }

        Save-Png -Bitmap $bmp -Path $PngPath
        Save-Icon -Bitmap $bmp -Path $IcoPath
    } finally {
        $g.Dispose()
        $bmp.Dispose()
        $bgPath.Dispose()
    }
}

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$iconPng = Join-Path $OutputDir "mt5-bot-icon.png"
$iconIco = Join-Path $OutputDir "mt5-bot-icon.ico"
$desktop = Join-Path $OutputDir "desktop-background.png"
$phone = Join-Path $OutputDir "phone-background.png"

New-IconArt -Size 256 -PngPath $iconPng -IcoPath $iconIco
New-Background -Width 1920 -Height 1080 -Path $desktop
New-Background -Width 1080 -Height 1920 -Path $phone

Write-Host "Created:"
Write-Host " - $iconPng"
Write-Host " - $iconIco"
Write-Host " - $desktop"
Write-Host " - $phone"
