import SwiftUI

/// Flash UI Analysis Cards - displays 3 analysis cards from a single prompt
struct AnalysisCardsView: View {
    let session: AnalysisSession
    @Binding var focusedIndex: Int?
    let onCardAction: (AnalysisArtifact, String) -> Void

    var body: some View {
        if let focused = focusedIndex {
            // Focused single card view
            FocusedCardView(
                artifact: session.artifacts[focused],
                currentIndex: focused,
                totalCount: session.artifacts.count,
                onPrevious: { focusedIndex = max(0, focused - 1) },
                onNext: { focusedIndex = min(session.artifacts.count - 1, focused + 1) },
                onOverview: { focusedIndex = nil },
                onAction: { action in onCardAction(session.artifacts[focused], action) }
            )
        } else {
            // Grid overview of all cards
            CardsGridView(
                artifacts: session.artifacts,
                onCardTapped: { index in focusedIndex = index }
            )
        }
    }
}

// MARK: - Cards Grid View

struct CardsGridView: View {
    let artifacts: [AnalysisArtifact]
    let onCardTapped: (Int) -> Void

    var body: some View {
        VStack(spacing: PNCTheme.Spacing.md) {
            // Header
            HStack {
                Text("STRATEGIC ANALYSIS")
                    .font(.system(size: 12, weight: .bold))
                    .foregroundColor(PNCTheme.Colors.darkGrey)
                    .kerning(2)

                Spacer()

                Text("\(artifacts.count) vectors synthesized")
                    .font(.system(size: 11))
                    .foregroundColor(PNCTheme.Colors.textSecondary)
            }
            .padding(.horizontal, PNCTheme.Spacing.lg)
            .padding(.top, PNCTheme.Spacing.md)

            // Cards Grid - fills available space
            HStack(spacing: PNCTheme.Spacing.md) {
                ForEach(Array(artifacts.enumerated()), id: \.element.id) { index, artifact in
                    AnalysisCard(
                        artifact: artifact,
                        onTap: { onCardTapped(index) }
                    )
                }
            }
            .padding(.horizontal, PNCTheme.Spacing.lg)
            .padding(.bottom, PNCTheme.Spacing.lg)
        }
        .frame(maxHeight: .infinity)
    }
}

// MARK: - Analysis Card

struct AnalysisCard: View {
    let artifact: AnalysisArtifact
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            VStack(alignment: .leading, spacing: 0) {
                // Card Header - compact
                HStack(spacing: 8) {
                    Rectangle()
                        .fill(PNCTheme.Colors.orange)
                        .frame(width: 3, height: 14)

                    Text(artifact.styleName.uppercased())
                        .font(.system(size: 9, weight: .bold))
                        .foregroundColor(PNCTheme.Colors.orange)
                        .kerning(1)

                    Spacer()

                    statusIndicator
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(PNCTheme.Colors.darkGrey)

                // Card Content - takes all available space
                ScrollView {
                    Text(PNCMarkdownRenderer.render(artifact.content))
                        .font(.system(size: 13))
                        .foregroundColor(PNCTheme.Colors.textPrimary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(12)
                }
                .frame(maxHeight: .infinity)

                // Card Footer - compact
                HStack {
                    Text("Click to expand")
                        .font(.system(size: 8))
                        .foregroundColor(PNCTheme.Colors.textSecondary)

                    Spacer()

                    Image(systemName: "arrow.up.left.and.arrow.down.right")
                        .font(.system(size: 9))
                        .foregroundColor(PNCTheme.Colors.textSecondary)
                }
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(PNCTheme.Colors.lightGrey)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(PNCTheme.Colors.white)
            .shadow(color: .black.opacity(0.05), radius: 4)
        }
        .buttonStyle(.plain)
        .pncCardHoverEffect()
    }

    @ViewBuilder
    private var statusIndicator: some View {
        switch artifact.status {
        case .streaming:
            HStack(spacing: 4) {
                ProgressView()
                    .scaleEffect(0.6)
                    .tint(PNCTheme.Colors.orange)
                Text("Synthesizing...")
                    .font(.system(size: 9))
                    .foregroundColor(PNCTheme.Colors.orange)
            }
        case .complete:
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 12))
                .foregroundColor(.green)
        case .error:
            Image(systemName: "exclamationmark.circle.fill")
                .font(.system(size: 12))
                .foregroundColor(.red)
        }
    }

}

// MARK: - Focused Card View

struct FocusedCardView: View {
    let artifact: AnalysisArtifact
    let currentIndex: Int
    let totalCount: Int
    let onPrevious: () -> Void
    let onNext: () -> Void
    let onOverview: () -> Void
    let onAction: (String) -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Navigation Header - compact
            HStack {
                Button(action: onOverview) {
                    HStack(spacing: 4) {
                        Image(systemName: "square.grid.2x2")
                            .font(.system(size: 10))
                        Text("OVERVIEW")
                            .font(.system(size: 9, weight: .bold))
                            .kerning(1)
                    }
                    .foregroundColor(PNCTheme.Colors.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(PNCTheme.Colors.darkGrey.opacity(0.8))
                }
                .buttonStyle(.plain)
                .pncHoverEffect()

                Spacer()

                // Navigation Arrows
                HStack(spacing: 12) {
                    Button(action: onPrevious) {
                        Image(systemName: "chevron.left")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(currentIndex > 0 ? PNCTheme.Colors.darkGrey : PNCTheme.Colors.darkGrey.opacity(0.3))
                            .frame(width: 28, height: 28)
                    }
                    .buttonStyle(.plain)
                    .disabled(currentIndex == 0)
                    .pncHoverEffect(showBorder: currentIndex > 0, scale: 1.1)

                    Text("\(currentIndex + 1) / \(totalCount)")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(PNCTheme.Colors.darkGrey)

                    Button(action: onNext) {
                        Image(systemName: "chevron.right")
                            .font(.system(size: 14, weight: .semibold))
                            .foregroundColor(currentIndex < totalCount - 1 ? PNCTheme.Colors.darkGrey : PNCTheme.Colors.darkGrey.opacity(0.3))
                            .frame(width: 28, height: 28)
                    }
                    .buttonStyle(.plain)
                    .disabled(currentIndex == totalCount - 1)
                    .pncHoverEffect(showBorder: currentIndex < totalCount - 1, scale: 1.1)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(PNCTheme.Colors.lightGrey)

            // Card Header - compact
            HStack(spacing: 8) {
                Rectangle()
                    .fill(PNCTheme.Colors.orange)
                    .frame(width: 3, height: 16)

                Text(artifact.styleName.uppercased())
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(PNCTheme.Colors.orange)
                    .kerning(1)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(PNCTheme.Colors.darkGrey)

            // Card Content - takes all available space
            ScrollView {
                Text(PNCMarkdownRenderer.render(artifact.content))
                    .font(.system(size: 14))
                    .foregroundColor(PNCTheme.Colors.textPrimary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
                    .textSelection(.enabled)
            }
            .frame(maxHeight: .infinity)
            .background(PNCTheme.Colors.white)

            // Action Button - compact
            Button(action: { onAction("FOUNDRY_SOLUTION") }) {
                HStack(spacing: 6) {
                    Image(systemName: "bolt.fill")
                        .font(.system(size: 11))
                    Text("INITIATE FOUNDRY SOLUTION")
                        .font(.system(size: 10, weight: .bold))
                        .kerning(1)
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 10)
                .background(PNCTheme.Colors.orange)
            }
            .buttonStyle(.plain)
            .pncHoverEffect(showBorder: false, scale: 1.02)
        }
    }
}

#Preview {
    let session = AnalysisSession(prompt: "Analyze Q3 retail spending")
    var modifiedSession = session
    modifiedSession.artifacts = [
        {
            var a = AnalysisArtifact(styleName: "Liquidity Analysis")
            a.content = "## Executive Summary\n\nYour Q3 retail spending shows strong momentum..."
            a.status = .complete
            return a
        }(),
        {
            var a = AnalysisArtifact(styleName: "Operational Trace")
            a.content = "## Key Findings\n\nOperational efficiency metrics indicate..."
            a.status = .complete
            return a
        }(),
        {
            var a = AnalysisArtifact(styleName: "Market Benchmarks")
            a.content = "## Sector Comparison\n\nCompared to industry peers..."
            a.status = .streaming
            return a
        }()
    ]

    return AnalysisCardsView(
        session: modifiedSession,
        focusedIndex: .constant(nil),
        onCardAction: { _, _ in }
    )
    .frame(width: 900, height: 400)
    .background(Color(hex: "F9F9F9"))
}
