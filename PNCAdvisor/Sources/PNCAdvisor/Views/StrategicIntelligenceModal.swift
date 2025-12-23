import SwiftUI

/// Modal showing detailed AI-generated strategic analysis for a stat or notification
struct StrategicIntelligenceModal: View {
    let title: String
    let subtitle: String
    @Binding var analysis: String
    let isLoading: Bool
    let actionButtonTitle: String?
    let onAction: (() -> Void)?
    let onDismiss: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Header
            modalHeader

            // Content
            ScrollView {
                VStack(alignment: .leading, spacing: PNCTheme.Spacing.lg) {
                    if isLoading {
                        loadingView
                    } else {
                        analysisContent
                    }
                }
                .padding(PNCTheme.Spacing.xl)
            }

            // Action Button
            if let buttonTitle = actionButtonTitle, !isLoading {
                actionButton(title: buttonTitle)
            }
        }
        .frame(width: 600, height: 500)
        .background(PNCTheme.Colors.white)
        .shadow(color: .black.opacity(0.2), radius: 20, x: 0, y: 10)
    }

    // MARK: - Header

    private var modalHeader: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("STRATEGIC INTELLIGENCE")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(PNCTheme.Colors.orange)
                        .kerning(2)

                    Text(title)
                        .font(.system(size: 20, weight: .bold))
                        .foregroundColor(PNCTheme.Colors.white)
                }

                Spacer()

                Button(action: onDismiss) {
                    Image(systemName: "xmark")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(PNCTheme.Colors.white.opacity(0.8))
                        .frame(width: 28, height: 28)
                }
                .buttonStyle(.plain)
                .pncHoverEffect(showBorder: false, scale: 1.1)
            }

            Text(subtitle)
                .font(.system(size: 12))
                .foregroundColor(PNCTheme.Colors.white.opacity(0.7))
        }
        .padding(PNCTheme.Spacing.lg)
        .background(PNCTheme.Colors.darkGrey)
    }

    // MARK: - Loading View

    private var loadingView: some View {
        VStack(spacing: PNCTheme.Spacing.lg) {
            ProgressView()
                .scaleEffect(1.5)
                .tint(PNCTheme.Colors.orange)

            Text("Accessing Global Map traces...")
                .font(.system(size: 14))
                .foregroundColor(PNCTheme.Colors.textSecondary)

            Text("Synthesizing strategic intelligence from cross-sector data...")
                .font(.system(size: 12))
                .foregroundColor(PNCTheme.Colors.textSecondary.opacity(0.7))
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.vertical, 60)
    }

    // MARK: - Analysis Content

    private var analysisContent: some View {
        VStack(alignment: .leading, spacing: PNCTheme.Spacing.lg) {
            // Analysis text with shared markdown rendering
            Text(PNCMarkdownRenderer.render(analysis))
                .font(.system(size: 14))
                .foregroundColor(PNCTheme.Colors.textPrimary)
                .textSelection(.enabled)
        }
    }

    // MARK: - Action Button

    private func actionButton(title: String) -> some View {
        Button(action: { onAction?() }) {
            HStack {
                Image(systemName: "bolt.fill")
                Text(title)
                    .font(.system(size: 12, weight: .bold))
                    .kerning(1)
            }
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, PNCTheme.Spacing.md)
            .background(PNCTheme.Colors.orange)
        }
        .buttonStyle(.plain)
        .pncHoverEffect(showBorder: false, scale: 1.02)
    }
}

#Preview {
    StrategicIntelligenceModal(
        title: "Liquidity Access Analysis",
        subtitle: "Deep-trace analysis of your $24.5M liquidity position",
        analysis: .constant("""
        ## Executive Summary

        Your current liquidity access of $24.5M positions you in the **top quartile** of middle-market industrial clients.

        ## Global Map Comparison

        Compared to sector peers:
        - Your liquidity ratio exceeds the median by 34%
        - Cash conversion cycle is 12 days faster than benchmark
        - Working capital efficiency scores at 87th percentile

        ## Actionable Strategy

        1. Consider deploying excess liquidity into short-term treasury instruments
        2. Evaluate credit line optimization opportunities
        3. Review sweep account configurations for yield enhancement
        """),
        isLoading: false,
        actionButtonTitle: "INITIATE TREASURY OPTIMIZATION",
        onAction: {},
        onDismiss: {}
    )
}
