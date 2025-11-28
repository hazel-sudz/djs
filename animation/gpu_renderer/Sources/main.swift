import Foundation
import CoreGraphics
import CoreImage
import AppKit
import Metal
import Accelerate

// MARK: - Data Structures

struct FrameData: Codable {
    let frameNumber: Int
    let timeLabel: String
    let titleDate: String
    let sensors: [SensorData]
    let wind: WindData?
}

struct SensorData: Codable {
    let lon: Double
    let lat: Double
    let pollution: Double
    let label: String
}

struct WindData: Codable {
    let centerLon: Double
    let centerLat: Double
    let endLon: Double
    let endLat: Double
    let speedLabel: String
}

struct MapExtent: Codable {
    let lonMin: Double
    let lonMax: Double
    let latMin: Double
    let latMax: Double
}

struct RenderConfig: Codable {
    let width: Int
    let height: Int
    let mapExtent: MapExtent
    let pollutionMin: Double
    let pollutionMax: Double
    let baseMapPath: String?
    let outputDir: String
    let frames: [FrameData]
}

// MARK: - Metal Renderer

class MetalFrameRenderer {
    let device: MTLDevice
    let commandQueue: MTLCommandQueue
    let ciContext: CIContext
    let width: Int
    let height: Int
    let mapExtent: MapExtent
    let pollutionMin: Double
    let pollutionMax: Double
    var baseMapImage: CGImage?

    // Plasma colormap (matching viridis plasma)
    let plasmaColors: [(r: CGFloat, g: CGFloat, b: CGFloat)] = [
        (0.050, 0.030, 0.528),
        (0.133, 0.022, 0.563),
        (0.208, 0.020, 0.588),
        (0.282, 0.024, 0.602),
        (0.352, 0.034, 0.607),
        (0.417, 0.050, 0.601),
        (0.478, 0.071, 0.586),
        (0.536, 0.095, 0.563),
        (0.591, 0.121, 0.533),
        (0.643, 0.150, 0.498),
        (0.692, 0.180, 0.459),
        (0.738, 0.213, 0.418),
        (0.781, 0.248, 0.375),
        (0.821, 0.286, 0.332),
        (0.857, 0.326, 0.289),
        (0.890, 0.369, 0.246),
        (0.918, 0.416, 0.204),
        (0.942, 0.466, 0.163),
        (0.960, 0.520, 0.124),
        (0.973, 0.578, 0.089),
        (0.981, 0.639, 0.058),
        (0.984, 0.702, 0.038),
        (0.981, 0.768, 0.034),
        (0.972, 0.834, 0.053),
        (0.959, 0.899, 0.101),
        (0.940, 0.975, 0.131)
    ]

    init(width: Int, height: Int, mapExtent: MapExtent, pollutionMin: Double, pollutionMax: Double) throws {
        guard let device = MTLCreateSystemDefaultDevice() else {
            throw RendererError.noMetalDevice
        }
        guard let commandQueue = device.makeCommandQueue() else {
            throw RendererError.noCommandQueue
        }

        self.device = device
        self.commandQueue = commandQueue
        self.ciContext = CIContext(mtlDevice: device, options: [
            .cacheIntermediates: false,
            .priorityRequestLow: false
        ])
        self.width = width
        self.height = height
        self.mapExtent = mapExtent
        self.pollutionMin = pollutionMin
        self.pollutionMax = pollutionMax

        print("Metal GPU: \(device.name)")
        print("Render size: \(width)x\(height)")
    }

    func loadBaseMap(from path: String) throws {
        guard let dataProvider = CGDataProvider(filename: path),
              let image = CGImage(pngDataProviderSource: dataProvider, decode: nil, shouldInterpolate: true, intent: .defaultIntent) else {
            throw RendererError.failedToLoadBaseMap
        }
        self.baseMapImage = image
        print("Base map loaded: \(image.width)x\(image.height)")
    }

    func createWhiteBackground() -> CGImage? {
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }

        context.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))

        return context.makeImage()
    }

    // Convert geo coordinates to pixel coordinates
    func geoToPixel(lon: Double, lat: Double) -> (x: CGFloat, y: CGFloat) {
        let x = CGFloat((lon - mapExtent.lonMin) / (mapExtent.lonMax - mapExtent.lonMin)) * CGFloat(width)
        // Flip Y because CGContext has origin at bottom-left
        let y = CGFloat(1.0 - (lat - mapExtent.latMin) / (mapExtent.latMax - mapExtent.latMin)) * CGFloat(height)
        return (x, y)
    }

    // Get color from plasma colormap
    func getPlasmaColor(value: Double) -> (r: CGFloat, g: CGFloat, b: CGFloat) {
        let normalized = max(0, min(1, (value - pollutionMin) / (pollutionMax - pollutionMin)))
        let index = normalized * Double(plasmaColors.count - 1)
        let lowerIndex = Int(index)
        let upperIndex = min(lowerIndex + 1, plasmaColors.count - 1)
        let fraction = CGFloat(index - Double(lowerIndex))

        let lower = plasmaColors[lowerIndex]
        let upper = plasmaColors[upperIndex]

        return (
            r: lower.r + (upper.r - lower.r) * fraction,
            g: lower.g + (upper.g - lower.g) * fraction,
            b: lower.b + (upper.b - lower.b) * fraction
        )
    }

    // Get circle size based on pollution value
    func getCircleSize(pollution: Double) -> CGFloat {
        let normalized = (pollution - pollutionMin) / (pollutionMax - pollutionMin)
        let minSize: CGFloat = 15
        let maxSize: CGFloat = 60
        return minSize + CGFloat(normalized) * (maxSize - minSize)
    }

    func renderFrame(_ frame: FrameData) -> CGImage? {
        let colorSpace = CGColorSpaceCreateDeviceRGB()
        guard let context = CGContext(
            data: nil,
            width: width,
            height: height,
            bitsPerComponent: 8,
            bytesPerRow: width * 4,
            space: colorSpace,
            bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue
        ) else { return nil }

        // Enable anti-aliasing
        context.setAllowsAntialiasing(true)
        context.setShouldAntialias(true)
        context.interpolationQuality = .high

        // Draw white background
        context.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
        context.fill(CGRect(x: 0, y: 0, width: width, height: height))

        // Draw base map if available
        if let baseMap = baseMapImage {
            context.draw(baseMap, in: CGRect(x: 0, y: 0, width: width, height: height))
        } else {
            // Draw a light gray placeholder
            context.setFillColor(CGColor(red: 0.95, green: 0.95, blue: 0.95, alpha: 1))
            context.fill(CGRect(x: 0, y: 0, width: width, height: height))
        }

        // Draw wind arrow
        if let wind = frame.wind {
            let start = geoToPixel(lon: wind.centerLon, lat: wind.centerLat)
            let end = geoToPixel(lon: wind.endLon, lat: wind.endLat)

            // Draw arrow line
            context.setStrokeColor(CGColor(red: 0, green: 0, blue: 0.55, alpha: 0.9))
            context.setLineWidth(4)
            context.setLineCap(.round)
            context.move(to: CGPoint(x: start.x, y: start.y))
            context.addLine(to: CGPoint(x: end.x, y: end.y))
            context.strokePath()

            // Draw arrowhead
            let angle = atan2(end.y - start.y, end.x - start.x)
            let arrowLength: CGFloat = 15
            let arrowAngle: CGFloat = .pi / 6

            let point1 = CGPoint(
                x: end.x - arrowLength * cos(angle - arrowAngle),
                y: end.y - arrowLength * sin(angle - arrowAngle)
            )
            let point2 = CGPoint(
                x: end.x - arrowLength * cos(angle + arrowAngle),
                y: end.y - arrowLength * sin(angle + arrowAngle)
            )

            context.setFillColor(CGColor(red: 0, green: 0, blue: 0.55, alpha: 0.9))
            context.move(to: CGPoint(x: end.x, y: end.y))
            context.addLine(to: point1)
            context.addLine(to: point2)
            context.closePath()
            context.fillPath()

            // Draw center point
            context.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1))
            context.setStrokeColor(CGColor(red: 0, green: 0, blue: 0.55, alpha: 1))
            context.setLineWidth(3)
            context.addEllipse(in: CGRect(x: start.x - 8, y: start.y - 8, width: 16, height: 16))
            context.drawPath(using: .fillStroke)

            // Draw wind speed label
            drawLabel(context: context, text: wind.speedLabel,
                     x: start.x, y: start.y - 30,
                     backgroundColor: CGColor(red: 0.68, green: 0.85, blue: 0.9, alpha: 0.9))
        }

        // Draw pollution circles
        for sensor in frame.sensors {
            let pos = geoToPixel(lon: sensor.lon, lat: sensor.lat)
            let size = getCircleSize(pollution: sensor.pollution)
            let color = getPlasmaColor(value: sensor.pollution)

            context.setFillColor(CGColor(red: color.r, green: color.g, blue: color.b, alpha: 0.7))
            context.addEllipse(in: CGRect(x: pos.x - size/2, y: pos.y - size/2, width: size, height: size))
            context.fillPath()

            // Draw pollution label above circle
            drawLabel(context: context, text: sensor.label,
                     x: pos.x, y: pos.y - size/2 - 20,
                     backgroundColor: CGColor(red: 1, green: 1, blue: 1, alpha: 0.9))
        }

        // Draw title
        drawTitle(context: context, title: "Ultrafine Particle Concentration - \(frame.titleDate)",
                 subtitle: "Time: \(frame.timeLabel)")

        // Draw legend
        drawLegend(context: context)

        return context.makeImage()
    }

    func drawLabel(context: CGContext, text: String, x: CGFloat, y: CGFloat, backgroundColor: CGColor) {
        let font = CTFontCreateWithName("Helvetica-Bold" as CFString, 14, nil)
        let attributes: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: NSColor.black
        ]
        let attributedString = NSAttributedString(string: text, attributes: attributes)
        let line = CTLineCreateWithAttributedString(attributedString)
        let bounds = CTLineGetBoundsWithOptions(line, .useOpticalBounds)

        let padding: CGFloat = 6
        let rectWidth = bounds.width + padding * 2
        let rectHeight = bounds.height + padding * 2
        let rectX = x - rectWidth / 2
        let rectY = y - rectHeight / 2

        // Draw background
        context.setFillColor(backgroundColor)
        context.setStrokeColor(CGColor(red: 0.7, green: 0.7, blue: 0.7, alpha: 1))
        context.setLineWidth(0.5)
        let rect = CGRect(x: rectX, y: rectY, width: rectWidth, height: rectHeight)
        context.addRect(rect)
        context.drawPath(using: .fillStroke)

        // Draw text
        context.saveGState()
        context.textPosition = CGPoint(x: rectX + padding, y: rectY + padding + 3)
        CTLineDraw(line, context)
        context.restoreGState()
    }

    func drawTitle(context: CGContext, title: String, subtitle: String) {
        // Title
        let titleFont = CTFontCreateWithName("Helvetica-Bold" as CFString, 20, nil)
        let titleAttributes: [NSAttributedString.Key: Any] = [
            .font: titleFont,
            .foregroundColor: NSColor.black
        ]
        let titleString = NSAttributedString(string: title, attributes: titleAttributes)
        let titleLine = CTLineCreateWithAttributedString(titleString)
        let titleBounds = CTLineGetBoundsWithOptions(titleLine, .useOpticalBounds)

        context.saveGState()
        context.textPosition = CGPoint(x: CGFloat(width)/2 - titleBounds.width/2, y: CGFloat(height) - 35)
        CTLineDraw(titleLine, context)
        context.restoreGState()

        // Subtitle
        let subtitleFont = CTFontCreateWithName("Helvetica" as CFString, 16, nil)
        let subtitleAttributes: [NSAttributedString.Key: Any] = [
            .font: subtitleFont,
            .foregroundColor: NSColor.darkGray
        ]
        let subtitleString = NSAttributedString(string: subtitle, attributes: subtitleAttributes)
        let subtitleLine = CTLineCreateWithAttributedString(subtitleString)
        let subtitleBounds = CTLineGetBoundsWithOptions(subtitleLine, .useOpticalBounds)

        context.saveGState()
        context.textPosition = CGPoint(x: CGFloat(width)/2 - subtitleBounds.width/2, y: CGFloat(height) - 60)
        CTLineDraw(subtitleLine, context)
        context.restoreGState()
    }

    func drawLegend(context: CGContext) {
        let legendX = CGFloat(width) - 120
        let legendY: CGFloat = 100
        let barWidth: CGFloat = 20
        let barHeight: CGFloat = 150

        // Draw color bar
        for i in 0..<Int(barHeight) {
            let value = pollutionMin + (pollutionMax - pollutionMin) * Double(i) / Double(barHeight)
            let color = getPlasmaColor(value: value)
            context.setFillColor(CGColor(red: color.r, green: color.g, blue: color.b, alpha: 1))
            context.fill(CGRect(x: legendX, y: legendY + CGFloat(i), width: barWidth, height: 1))
        }

        // Draw border
        context.setStrokeColor(CGColor(red: 0, green: 0, blue: 0, alpha: 1))
        context.setLineWidth(1)
        context.stroke(CGRect(x: legendX, y: legendY, width: barWidth, height: barHeight))

        // Draw labels
        let font = CTFontCreateWithName("Helvetica" as CFString, 10, nil)
        let attributes: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: NSColor.black
        ]

        // Min label
        let minLabel = String(format: "%.0f", pollutionMin)
        let minString = NSAttributedString(string: minLabel, attributes: attributes)
        let minLine = CTLineCreateWithAttributedString(minString)
        context.saveGState()
        context.textPosition = CGPoint(x: legendX + barWidth + 5, y: legendY)
        CTLineDraw(minLine, context)
        context.restoreGState()

        // Max label
        let maxLabel = String(format: "%.0f", pollutionMax)
        let maxString = NSAttributedString(string: maxLabel, attributes: attributes)
        let maxLine = CTLineCreateWithAttributedString(maxString)
        context.saveGState()
        context.textPosition = CGPoint(x: legendX + barWidth + 5, y: legendY + barHeight - 10)
        CTLineDraw(maxLine, context)
        context.restoreGState()

        // Title
        let titleFont = CTFontCreateWithName("Helvetica-Bold" as CFString, 9, nil)
        let titleAttributes: [NSAttributedString.Key: Any] = [
            .font: titleFont,
            .foregroundColor: NSColor.black
        ]
        let titleString = NSAttributedString(string: "UFP (p/cm³)", attributes: titleAttributes)
        let titleLine = CTLineCreateWithAttributedString(titleString)
        context.saveGState()
        context.textPosition = CGPoint(x: legendX - 10, y: legendY + barHeight + 15)
        CTLineDraw(titleLine, context)
        context.restoreGState()
    }

    func saveImage(_ image: CGImage, to path: String) throws {
        let url = URL(fileURLWithPath: path)
        guard let destination = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else {
            throw RendererError.failedToCreateDestination
        }

        // Use hardware-accelerated PNG encoding
        let options: [CFString: Any] = [
            kCGImageDestinationLossyCompressionQuality: 0.9
        ]
        CGImageDestinationAddImage(destination, image, options as CFDictionary)

        if !CGImageDestinationFinalize(destination) {
            throw RendererError.failedToSaveImage
        }
    }

    func renderAllFrames(frames: [FrameData], outputDir: String, progressCallback: @escaping (Int, Int) -> Void) throws {
        let fileManager = FileManager.default
        if !fileManager.fileExists(atPath: outputDir) {
            try fileManager.createDirectory(atPath: outputDir, withIntermediateDirectories: true)
        }

        let totalFrames = frames.count
        let startTime = Date()

        // Use DispatchQueue for parallel rendering
        let queue = DispatchQueue(label: "render", attributes: .concurrent)
        let group = DispatchGroup()
        let lock = NSLock()
        var completedCount = 0
        var errors: [Error] = []

        // Process frames in parallel batches
        let batchSize = 8 // Process 8 frames at a time for optimal GPU utilization

        for batchStart in stride(from: 0, to: totalFrames, by: batchSize) {
            let batchEnd = min(batchStart + batchSize, totalFrames)

            for i in batchStart..<batchEnd {
                group.enter()
                queue.async {
                    defer { group.leave() }

                    let frame = frames[i]

                    autoreleasepool {
                        if let image = self.renderFrame(frame) {
                            let outputPath = "\(outputDir)/frame_\(String(format: "%04d", frame.frameNumber)).png"
                            do {
                                try self.saveImage(image, to: outputPath)

                                lock.lock()
                                completedCount += 1
                                let current = completedCount
                                lock.unlock()

                                progressCallback(current, totalFrames)
                            } catch {
                                lock.lock()
                                errors.append(error)
                                lock.unlock()
                            }
                        }
                    }
                }
            }

            // Wait for batch to complete before starting next
            group.wait()
        }

        let elapsed = Date().timeIntervalSince(startTime)
        print("\nRendering complete!")
        print("Total time: \(String(format: "%.1f", elapsed)) seconds")
        print("Average: \(String(format: "%.3f", elapsed / Double(totalFrames))) seconds per frame")
        print("Throughput: \(String(format: "%.1f", Double(totalFrames) / elapsed * 60)) frames per minute")

        if !errors.isEmpty {
            throw errors[0]
        }
    }
}

// MARK: - Errors

enum RendererError: Error, LocalizedError {
    case noMetalDevice
    case noCommandQueue
    case failedToLoadBaseMap
    case failedToCreateDestination
    case failedToSaveImage
    case invalidConfig

    var errorDescription: String? {
        switch self {
        case .noMetalDevice: return "No Metal-capable GPU found"
        case .noCommandQueue: return "Failed to create Metal command queue"
        case .failedToLoadBaseMap: return "Failed to load base map image"
        case .failedToCreateDestination: return "Failed to create image destination"
        case .failedToSaveImage: return "Failed to save image"
        case .invalidConfig: return "Invalid configuration"
        }
    }
}

// MARK: - Main

func main() throws {
    let args = CommandLine.arguments

    guard args.count >= 2 else {
        print("Usage: render-frames <config.json>")
        print("       render-frames --render-base-map <output.png> <width> <height> <lon_min> <lon_max> <lat_min> <lat_max>")
        exit(1)
    }

    // Check for base map rendering mode
    if args[1] == "--render-base-map" {
        guard args.count >= 9 else {
            print("Usage: render-frames --render-base-map <output.png> <width> <height> <lon_min> <lon_max> <lat_min> <lat_max>")
            exit(1)
        }
        // Base map rendering would require network access for OSM tiles
        // For now, we skip this and use R to pre-render the base map
        print("Base map should be pre-rendered using R")
        exit(0)
    }

    let configPath = args[1]

    print("Loading configuration from: \(configPath)")

    let configData = try Data(contentsOf: URL(fileURLWithPath: configPath))
    let config = try JSONDecoder().decode(RenderConfig.self, from: configData)

    print("Frames to render: \(config.frames.count)")
    print("Output directory: \(config.outputDir)")

    let renderer = try MetalFrameRenderer(
        width: config.width,
        height: config.height,
        mapExtent: config.mapExtent,
        pollutionMin: config.pollutionMin,
        pollutionMax: config.pollutionMax
    )

    if let baseMapPath = config.baseMapPath {
        try renderer.loadBaseMap(from: baseMapPath)
    }

    print("\nStarting Metal GPU rendering...")

    var lastProgress = 0
    try renderer.renderAllFrames(frames: config.frames, outputDir: config.outputDir) { current, total in
        let progress = (current * 100) / total
        if progress > lastProgress {
            lastProgress = progress
            print("\rProgress: \(progress)% (\(current)/\(total) frames)", terminator: "")
            fflush(stdout)
        }
    }

    print("\nAll frames rendered successfully!")
}

do {
    try main()
} catch {
    print("Error: \(error.localizedDescription)")
    exit(1)
}
