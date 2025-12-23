// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "PNCAdvisor",
    platforms: [
        .macOS(.v14)
    ],
    products: [
        .executable(name: "PNCAdvisor", targets: ["PNCAdvisor"])
    ],
    dependencies: [
        .package(url: "https://github.com/ml-explore/mlx-swift-lm.git", from: "2.29.0")
    ],
    targets: [
        .executableTarget(
            name: "PNCAdvisor",
            dependencies: [
                .product(name: "MLXLLM", package: "mlx-swift-lm"),
                .product(name: "MLXLMCommon", package: "mlx-swift-lm")
            ],
            path: "Sources/PNCAdvisor",
            resources: [
                .process("Assets.xcassets"),
                .copy("AppIcon.png")
            ]
        )
    ]
)
