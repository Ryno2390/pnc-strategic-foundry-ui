import SwiftUI

/// Landing screen with PNC Strategic Foundry branding
struct HomeView: View {
    let onPromptSelected: (String) -> Void
    let onStartChat: () -> Void

    @State private var hoveredPromptIndex: Int?

    var body: some View {
        ZStack {
            // Background
            PNCTheme.Colors.lightGrey
                .ignoresSafeArea()

            VStack(spacing: PNCTheme.Spacing.xl) {
                Spacer()

                // Branding Section
                VStack(spacing: PNCTheme.Spacing.md) {
                    Text("BRILLIANTLY BORING SINCE 1865")
                        .pncTagline()

                    HStack(spacing: 0) {
                        Text("STRATEGIC ")
                            .pncTitle()
                        Text("FOUNDRY")
                            .font(PNCTheme.Typography.titleLarge)
                            .foregroundColor(PNCTheme.Colors.orange)
                            .textCase(.uppercase)
                            .kerning(-2)
                    }

                    Text("PNC STRATEGIC FOUNDRY ADVISOR")
                        .font(PNCTheme.Typography.headline)
                        .foregroundColor(PNCTheme.Colors.darkGrey)
                        .textCase(.uppercase)
                        .kerning(2)
                        .padding(.top, PNCTheme.Spacing.xs)

                    Text("Unique non-obvious insights for the middle market.")
                        .font(PNCTheme.Typography.body)
                        .foregroundColor(PNCTheme.Colors.textSecondary)
                        .padding(.top, PNCTheme.Spacing.sm)
                }

                // Sample Prompts Section
                VStack(alignment: .center, spacing: PNCTheme.Spacing.md) {
                    Text("RECENT STRATEGIC INQUIRIES")
                        .pncLabel()
                        .padding(.bottom, PNCTheme.Spacing.xs)

                    VStack(spacing: PNCTheme.Spacing.sm) {
                        ForEach(Array(SamplePrompts.all.prefix(4).enumerated()), id: \.offset) { index, prompt in
                            PromptButton(
                                text: prompt,
                                isHovered: hoveredPromptIndex == index,
                                onHover: { hovering in
                                    hoveredPromptIndex = hovering ? index : nil
                                },
                                action: {
                                    onPromptSelected(prompt)
                                }
                            )
                        }
                    }
                }
                .padding(.top, PNCTheme.Spacing.xl)

                Spacer()

                // Start Chat Button
                Button(action: onStartChat) {
                    HStack {
                        Text("BEGIN STRATEGIC SESSION")
                        Image(systemName: "arrow.right")
                    }
                }
                .buttonStyle(PNCOrangeButtonStyle())
                .padding(.bottom, PNCTheme.Spacing.xxl)
            }
            .padding(.horizontal, PNCTheme.Spacing.xxl)
        }
    }
}

/// Individual prompt button component
struct PromptButton: View {
    let text: String
    let isHovered: Bool
    let onHover: (Bool) -> Void
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack {
                Text(text)
                    .font(PNCTheme.Typography.bodyBold)
                    .foregroundColor(isHovered ? PNCTheme.Colors.orange : PNCTheme.Colors.darkGrey)
                    .lineLimit(1)

                Spacer()

                Image(systemName: "arrow.right")
                    .foregroundColor(isHovered ? PNCTheme.Colors.orange : PNCTheme.Colors.textSecondary)
                    .opacity(isHovered ? 1 : 0.5)
            }
            .padding(.horizontal, PNCTheme.Spacing.lg)
            .padding(.vertical, PNCTheme.Spacing.md)
            .background(
                Rectangle()
                    .fill(isHovered ? PNCTheme.Colors.white : PNCTheme.Colors.darkGrey.opacity(0.04))
            )
            .overlay(
                Rectangle()
                    .stroke(isHovered ? PNCTheme.Colors.orange : PNCTheme.Colors.borderColor, lineWidth: 1)
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                onHover(hovering)
            }
        }
        .frame(maxWidth: 500)
    }
}

#Preview {
    HomeView(
        onPromptSelected: { _ in },
        onStartChat: {}
    )
    .frame(width: 800, height: 600)
}
