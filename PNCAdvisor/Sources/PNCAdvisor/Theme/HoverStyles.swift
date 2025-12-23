import SwiftUI

/// Consistent hover style for all interactive elements
/// Applies slight scale and PNC Orange border on hover
struct PNCHoverStyle: ViewModifier {
    @State private var isHovered = false
    var showBorder: Bool = true
    var scaleAmount: CGFloat = 1.02

    func body(content: Content) -> some View {
        content
            .scaleEffect(isHovered ? scaleAmount : 1.0)
            .background(
                RoundedRectangle(cornerRadius: 4)
                    .stroke(isHovered && showBorder ? PNCTheme.Colors.orange : Color.clear, lineWidth: 2)
            )
            .animation(.easeInOut(duration: 0.15), value: isHovered)
            .onHover { hovering in
                isHovered = hovering
            }
    }
}

/// Hover style for circular buttons (like profile icon)
struct PNCCircleHoverStyle: ViewModifier {
    @State private var isHovered = false

    func body(content: Content) -> some View {
        content
            .scaleEffect(isHovered ? 1.05 : 1.0)
            .background(
                Circle()
                    .stroke(isHovered ? PNCTheme.Colors.orange : Color.clear, lineWidth: 2)
            )
            .animation(.easeInOut(duration: 0.15), value: isHovered)
            .onHover { hovering in
                isHovered = hovering
            }
    }
}

/// Hover style for card-like elements
struct PNCCardHoverStyle: ViewModifier {
    @State private var isHovered = false

    func body(content: Content) -> some View {
        content
            .scaleEffect(isHovered ? 1.01 : 1.0)
            .background(
                Rectangle()
                    .stroke(isHovered ? PNCTheme.Colors.orange : Color.clear, lineWidth: 2)
            )
            .shadow(color: .black.opacity(isHovered ? 0.1 : 0.05), radius: isHovered ? 8 : 4)
            .animation(.easeInOut(duration: 0.15), value: isHovered)
            .onHover { hovering in
                isHovered = hovering
            }
    }
}

// MARK: - View Extensions

extension View {
    /// Apply consistent PNC hover style with orange border and slight scale
    func pncHoverEffect(showBorder: Bool = true, scale: CGFloat = 1.02) -> some View {
        self.modifier(PNCHoverStyle(showBorder: showBorder, scaleAmount: scale))
    }

    /// Apply circular hover style for round buttons
    func pncCircleHoverEffect() -> some View {
        self.modifier(PNCCircleHoverStyle())
    }

    /// Apply card hover style for larger card elements
    func pncCardHoverEffect() -> some View {
        self.modifier(PNCCardHoverStyle())
    }
}
