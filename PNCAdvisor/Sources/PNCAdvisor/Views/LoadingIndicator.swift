import SwiftUI

/// PNC-styled loading indicator with progress bar animation
struct LoadingIndicator: View {
    let status: String

    @State private var animationOffset: CGFloat = -1.0

    var body: some View {
        VStack(spacing: PNCTheme.Spacing.md) {
            // Status text
            Text(status.uppercased())
                .font(PNCTheme.Typography.caption)
                .foregroundColor(PNCTheme.Colors.darkGrey)
                .kerning(1)

            // Progress bar
            GeometryReader { geometry in
                ZStack(alignment: .leading) {
                    // Background track
                    Rectangle()
                        .fill(PNCTheme.Colors.darkGrey.opacity(0.1))

                    // Animated fill
                    Rectangle()
                        .fill(PNCTheme.Colors.orange)
                        .frame(width: geometry.size.width * 0.4)
                        .offset(x: animationOffset * geometry.size.width)
                }
            }
            .frame(height: 4)
            .clipped()
            .onAppear {
                withAnimation(
                    Animation
                        .easeInOut(duration: 2.0)
                        .repeatForever(autoreverses: false)
                ) {
                    animationOffset = 1.0
                }
            }
        }
        .frame(maxWidth: 300)
    }
}

/// Full-screen loading view for model initialization
struct ModelLoadingView: View {
    let status: String
    let errorMessage: String?
    let onRetry: () -> Void

    var body: some View {
        ZStack {
            PNCTheme.Colors.lightGrey
                .ignoresSafeArea()

            VStack(spacing: PNCTheme.Spacing.xl) {
                // PNC Logo placeholder
                VStack(spacing: PNCTheme.Spacing.sm) {
                    Text("PNC")
                        .font(.system(size: 36, weight: .black))
                        .foregroundColor(PNCTheme.Colors.darkGrey)

                    Text("STRATEGIC FOUNDRY")
                        .font(PNCTheme.Typography.caption)
                        .foregroundColor(PNCTheme.Colors.orange)
                        .kerning(2)
                }

                if let error = errorMessage {
                    // Error state
                    VStack(spacing: PNCTheme.Spacing.md) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .font(.system(size: 32))
                            .foregroundColor(PNCTheme.Colors.orange)

                        Text(error)
                            .font(PNCTheme.Typography.body)
                            .foregroundColor(PNCTheme.Colors.textSecondary)
                            .multilineTextAlignment(.center)
                            .frame(maxWidth: 400)

                        Button("Retry") {
                            onRetry()
                        }
                        .buttonStyle(PNCButtonStyle())
                        .padding(.top, PNCTheme.Spacing.md)
                    }
                } else {
                    // Loading state
                    LoadingIndicator(status: status)
                        .padding(.top, PNCTheme.Spacing.xl)
                }
            }
        }
    }
}

#Preview("Loading") {
    LoadingIndicator(status: "Loading model weights...")
        .padding()
        .frame(width: 400)
}

#Preview("Model Loading Screen") {
    ModelLoadingView(
        status: "Loading PNC Strategic Advisor model...",
        errorMessage: nil,
        onRetry: {}
    )
    .frame(width: 600, height: 400)
}

#Preview("Error State") {
    ModelLoadingView(
        status: "",
        errorMessage: "Failed to load model. Please check that the model files exist at the specified path.",
        onRetry: {}
    )
    .frame(width: 600, height: 400)
}
