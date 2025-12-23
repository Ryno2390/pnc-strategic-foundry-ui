import SwiftUI

/// Chat message bubble with PNC styling
struct MessageBubble: View {
    let message: ChatMessage
    let isStreaming: Bool

    init(message: ChatMessage, isStreaming: Bool = false) {
        self.message = message
        self.isStreaming = isStreaming
    }

    var body: some View {
        HStack(alignment: .top, spacing: PNCTheme.Spacing.md) {
            switch message.role {
            case .user:
                Spacer(minLength: 60)
                userBubble

            case .advisor:
                advisorBubble
                Spacer(minLength: 60)

            case .system:
                Spacer()
                systemBubble
                Spacer()
            }
        }
        .padding(.horizontal, PNCTheme.Spacing.md)
    }

    // MARK: - User Message
    private var userBubble: some View {
        VStack(alignment: .trailing, spacing: PNCTheme.Spacing.xs) {
            Text(message.content)
                .font(PNCTheme.Typography.body)
                .foregroundColor(PNCTheme.Colors.white)
                .padding(PNCTheme.Spacing.md)
                .background(PNCTheme.Colors.darkGrey)
                .textSelection(.enabled)

            Text(formattedTime)
                .font(.system(size: 10))
                .foregroundColor(PNCTheme.Colors.textSecondary)
        }
    }

    // MARK: - Advisor Message
    private var advisorBubble: some View {
        HStack(alignment: .top, spacing: PNCTheme.Spacing.sm) {
            // Orange accent bar
            Rectangle()
                .fill(PNCTheme.Colors.orange)
                .frame(width: 4)

            VStack(alignment: .leading, spacing: PNCTheme.Spacing.xs) {
                // Advisor label
                Text("SARAH V. • STRATEGIC ADVISOR")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(PNCTheme.Colors.orange)
                    .kerning(1)

                // Message content
                if message.content.isEmpty && isStreaming {
                    streamingPlaceholder
                } else {
                    Text(PNCMarkdownRenderer.render(message.content))
                        .font(PNCTheme.Typography.body)
                        .foregroundColor(PNCTheme.Colors.textPrimary)
                        .textSelection(.enabled)
                }

                // Timestamp
                Text(formattedTime)
                    .font(.system(size: 10))
                    .foregroundColor(PNCTheme.Colors.textSecondary)
            }
            .padding(PNCTheme.Spacing.md)
            .background(PNCTheme.Colors.lightGrey.opacity(0.5))
        }
        .fixedSize(horizontal: false, vertical: true)
    }

    // MARK: - System Message
    private var systemBubble: some View {
        Text(message.content)
            .font(PNCTheme.Typography.caption)
            .foregroundColor(PNCTheme.Colors.textSecondary)
            .italic()
            .padding(.horizontal, PNCTheme.Spacing.md)
            .padding(.vertical, PNCTheme.Spacing.sm)
            .background(
                RoundedRectangle(cornerRadius: 4)
                    .stroke(style: StrokeStyle(lineWidth: 1, dash: [4]))
                    .foregroundColor(PNCTheme.Colors.borderColor)
            )
    }

    // MARK: - Streaming Placeholder
    private var streamingPlaceholder: some View {
        HStack(spacing: 4) {
            ForEach(0..<3, id: \.self) { index in
                Circle()
                    .fill(PNCTheme.Colors.orange)
                    .frame(width: 6, height: 6)
                    .opacity(0.4)
                    .animation(
                        Animation
                            .easeInOut(duration: 0.6)
                            .repeatForever()
                            .delay(Double(index) * 0.2),
                        value: isStreaming
                    )
            }
            Text("Accessing Global Map traces...")
                .font(PNCTheme.Typography.caption)
                .foregroundColor(PNCTheme.Colors.textSecondary)
        }
    }

    // MARK: - Helpers
    private var formattedTime: String {
        let formatter = DateFormatter()
        formatter.timeStyle = .short
        return formatter.string(from: message.timestamp)
    }
}

#Preview("User Message") {
    MessageBubble(
        message: ChatMessage(
            role: .user,
            content: "What are the key risks facing middle-market manufacturers?"
        )
    )
    .frame(width: 600)
    .padding()
}

#Preview("Advisor Message") {
    MessageBubble(
        message: ChatMessage(
            role: .advisor,
            content: "Based on our analysis of middle-market manufacturing data, three primary risk factors warrant attention:\n\n1. Supply Chain Concentration\n2. Working Capital Pressure\n3. Labor Market Tightness"
        )
    )
    .frame(width: 600)
    .padding()
}

#Preview("Streaming") {
    MessageBubble(
        message: ChatMessage(role: .advisor, content: ""),
        isStreaming: true
    )
    .frame(width: 600)
    .padding()
}
