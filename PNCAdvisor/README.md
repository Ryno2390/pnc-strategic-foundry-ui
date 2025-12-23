# PNC Strategic Advisor - macOS App

A native SwiftUI macOS application that runs the PNC Strategic Advisor locally using Apple's MLX framework and a 4-bit quantized Qwen 2.5 3B model.

## Features

- **100% Local Inference**: All AI processing happens on-device using Apple Silicon
- **1.6GB Model**: 4-bit quantized for efficient memory usage (~2GB peak RAM)
- **~55 tokens/second**: Fast generation on M-series Macs
- **PNC Brand Design**: "Brilliantly Boring" professional aesthetic
- **Streaming Responses**: Real-time token-by-token generation

## Requirements

- macOS 14.0 (Sonoma) or later
- Apple Silicon Mac (M1/M2/M3/M4)
- Xcode 15.0 or later
- ~2GB available RAM during inference

## Quick Start

### 1. Open in Xcode

```bash
open PNCAdvisor/Package.swift
```

Or: File > Open > Select `PNCAdvisor/Package.swift`

### 2. Wait for Package Resolution

Xcode will automatically fetch the MLX Swift dependencies. This may take a few minutes on first open.

### 3. Select Scheme and Build

1. Select **"PNCAdvisor"** scheme (top left dropdown)
2. Select **"My Mac"** as the run destination
3. Press **Cmd+R** to build and run

### 4. Model Path

The app expects the quantized model at:
```
/Users/ryneschultz/pnc-strategic-foundry/outputs/pnc-advisor-4bit/
```

If you need to change this path, edit `AdvisorViewModel.swift`:
```swift
init(modelPath: String = "/your/custom/path/to/model")
```

## Project Structure

```
PNCAdvisor/
├── Package.swift                    # Swift Package manifest
├── Sources/PNCAdvisor/
│   ├── PNCAdvisorApp.swift          # App entry point
│   ├── ContentView.swift            # Main navigation container
│   ├── Models/
│   │   └── ChatMessage.swift        # Message data model
│   ├── ViewModels/
│   │   └── AdvisorViewModel.swift   # MLX model integration
│   ├── Views/
│   │   ├── HomeView.swift           # Landing screen
│   │   ├── ChatView.swift           # Chat interface
│   │   ├── MessageBubble.swift      # Message component
│   │   └── LoadingIndicator.swift   # Loading animation
│   └── Theme/
│       └── PNCTheme.swift           # PNC design system
└── README.md
```

## Dependencies

- [mlx-swift-lm](https://github.com/ml-explore/mlx-swift-lm) - Apple's MLX framework for Swift LLM inference

## Troubleshooting

### "Model not found" Error
Ensure the model files exist at the expected path:
```bash
ls -la /Users/ryneschultz/pnc-strategic-foundry/outputs/pnc-advisor-4bit/
```

Expected files:
- `model.safetensors` (1.6GB)
- `config.json`
- `tokenizer.json`
- `tokenizer_config.json`

### Build Fails with Metal Errors
MLX requires Xcode (not just Command Line Tools) to compile Metal shaders. Ensure you're building from within Xcode, not from the terminal.

### Out of Memory
The 4-bit model requires approximately 2GB of RAM. Close other memory-intensive applications if you encounter memory issues.

## License

Proprietary - PNC Bank Internal Use Only
