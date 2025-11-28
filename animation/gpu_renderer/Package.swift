// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "MetalFrameRenderer",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "render-frames",
            path: "Sources"
        )
    ]
)
