import SwiftUI
import AppKit

/// Animated dotted background effect matching the React UI
struct DottedBackground: View {
    @State private var phase: Double = 0

    let dotColor = PNCTheme.Colors.orange.opacity(0.3)
    let glowColor = PNCTheme.Colors.orange
    let gap: CGFloat = 40
    let dotRadius: CGFloat = 2

    var body: some View {
        Canvas { context, size in
            let columns = Int(size.width / gap) + 1
            let rows = Int(size.height / gap) + 1

            for row in 0..<rows {
                for col in 0..<columns {
                    let x = CGFloat(col) * gap + gap / 2
                    let y = CGFloat(row) * gap + gap / 2

                    // Calculate glow intensity based on position and phase
                    let distance = sqrt(pow(x - size.width / 2, 2) + pow(y - size.height / 2, 2))
                    let maxDistance = sqrt(pow(size.width / 2, 2) + pow(size.height / 2, 2))
                    let normalizedDistance = distance / maxDistance

                    // Create wave effect
                    let waveOffset = sin(normalizedDistance * 4 + phase) * 0.5 + 0.5
                    let glowIntensity = waveOffset * 0.6

                    // Random-ish selection for which dots glow
                    let shouldGlow = (row + col + Int(phase * 2)) % 7 == 0

                    if shouldGlow {
                        // Glowing dot
                        let glowRect = CGRect(
                            x: x - dotRadius * 2,
                            y: y - dotRadius * 2,
                            width: dotRadius * 4,
                            height: dotRadius * 4
                        )
                        context.fill(
                            Circle().path(in: glowRect),
                            with: .color(glowColor.opacity(glowIntensity * 0.5))
                        )
                    }

                    // Regular dot
                    let dotRect = CGRect(
                        x: x - dotRadius,
                        y: y - dotRadius,
                        width: dotRadius * 2,
                        height: dotRadius * 2
                    )
                    context.fill(
                        Circle().path(in: dotRect),
                        with: .color(shouldGlow ? glowColor.opacity(0.8) : dotColor)
                    )
                }
            }
        }
        .onAppear {
            withAnimation(.linear(duration: 8).repeatForever(autoreverses: false)) {
                phase = .pi * 2
            }
        }
        .background(Color(hex: "F8F8F8"))
    }
}

#Preview {
    DottedBackground()
        .frame(width: 800, height: 600)
}
