import SwiftUI

/// PNC Brand Design System
/// "Brilliantly Boring" - Professional, High-Trust Aesthetic
enum PNCTheme {
    // MARK: - Colors
    enum Colors {
        static let orange = Color(hex: "EF6A00")
        static let darkGrey = Color(hex: "333F48")
        static let lightGrey = Color(hex: "EDEDEE")
        static let white = Color.white
        static let textPrimary = darkGrey
        static let textSecondary = Color(hex: "5A6B78")
        static let borderColor = darkGrey.opacity(0.15)
    }

    // MARK: - Typography
    enum Typography {
        static let titleLarge = Font.system(size: 48, weight: .heavy, design: .default)
        static let titleMedium = Font.system(size: 24, weight: .heavy, design: .default)
        static let headline = Font.system(size: 18, weight: .bold, design: .default)
        static let body = Font.system(size: 16, weight: .regular, design: .default)
        static let bodyBold = Font.system(size: 16, weight: .semibold, design: .default)
        static let caption = Font.system(size: 12, weight: .bold, design: .default)
        static let tagline = Font.system(size: 14, weight: .heavy, design: .default)
    }

    // MARK: - Spacing
    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
        static let xxl: CGFloat = 48
    }
}

// MARK: - Color Extension for Hex Support
extension Color {
    init(hex: String) {
        let hex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: hex).scanHexInt64(&int)
        let a, r, g, b: UInt64
        switch hex.count {
        case 3: // RGB (12-bit)
            (a, r, g, b) = (255, (int >> 8) * 17, (int >> 4 & 0xF) * 17, (int & 0xF) * 17)
        case 6: // RGB (24-bit)
            (a, r, g, b) = (255, int >> 16, int >> 8 & 0xFF, int & 0xFF)
        case 8: // ARGB (32-bit)
            (a, r, g, b) = (int >> 24, int >> 16 & 0xFF, int >> 8 & 0xFF, int & 0xFF)
        default:
            (a, r, g, b) = (1, 1, 1, 0)
        }
        self.init(
            .sRGB,
            red: Double(r) / 255,
            green: Double(g) / 255,
            blue: Double(b) / 255,
            opacity: Double(a) / 255
        )
    }
}

// MARK: - View Modifiers
struct PNCButtonStyle: ButtonStyle {
    var isPrimary: Bool = true

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(PNCTheme.Typography.caption)
            .foregroundColor(isPrimary ? PNCTheme.Colors.white : PNCTheme.Colors.darkGrey)
            .padding(.horizontal, PNCTheme.Spacing.lg)
            .padding(.vertical, PNCTheme.Spacing.md)
            .background(isPrimary ? PNCTheme.Colors.darkGrey : Color.clear)
            .overlay(
                Rectangle()
                    .stroke(PNCTheme.Colors.darkGrey, lineWidth: isPrimary ? 0 : 2)
            )
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

struct PNCOrangeButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(PNCTheme.Typography.caption)
            .foregroundColor(PNCTheme.Colors.white)
            .padding(.horizontal, PNCTheme.Spacing.lg)
            .padding(.vertical, PNCTheme.Spacing.md)
            .background(PNCTheme.Colors.orange)
            .scaleEffect(configuration.isPressed ? 0.98 : 1.0)
            .animation(.easeInOut(duration: 0.1), value: configuration.isPressed)
    }
}

// MARK: - Text Styles
extension View {
    func pncTagline() -> some View {
        self
            .font(PNCTheme.Typography.tagline)
            .foregroundColor(PNCTheme.Colors.orange)
            .textCase(.uppercase)
            .kerning(3)
    }

    func pncTitle() -> some View {
        self
            .font(PNCTheme.Typography.titleLarge)
            .foregroundColor(PNCTheme.Colors.darkGrey)
            .textCase(.uppercase)
            .kerning(-2)
    }

    func pncLabel() -> some View {
        self
            .font(PNCTheme.Typography.caption)
            .foregroundColor(PNCTheme.Colors.textSecondary)
            .textCase(.uppercase)
            .kerning(1.5)
    }
}

// MARK: - Markdown Rendering Utilities

/// Shared markdown rendering for consistent output formatting across the app
enum PNCMarkdownRenderer {

    /// Renders markdown content as formatted AttributedString
    static func render(_ text: String) -> AttributedString {
        let processedText = preprocessMarkdown(text)

        do {
            let attributed = try AttributedString(markdown: processedText, options: AttributedString.MarkdownParsingOptions(
                interpretedSyntax: .inlineOnlyPreservingWhitespace
            ))
            return attributed
        } catch {
            return AttributedString(text)
        }
    }

    /// Pre-processes markdown to convert unsupported elements to readable text
    static func preprocessMarkdown(_ text: String) -> String {
        let lines = text.split(separator: "\n", omittingEmptySubsequences: false).map(String.init)
        var result: [String] = []
        var inTable = false
        var tableRows: [[String]] = []

        for line in lines {
            let trimmed = line.trimmingCharacters(in: .whitespaces)

            // Handle headers - convert to bold with visual separator
            if trimmed.hasPrefix("#") {
                // Flush any pending table
                if !tableRows.isEmpty {
                    result.append(contentsOf: formatTable(tableRows))
                    tableRows = []
                }
                inTable = false

                var content = trimmed
                while content.hasPrefix("#") {
                    content.removeFirst()
                }
                content = content.trimmingCharacters(in: .whitespaces)
                result.append("")
                result.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
                result.append("**\(content.uppercased())**")
                result.append("━━━━━━━━━━━━━━━━━━━━━━━━━")
                result.append("")
                continue
            }

            // Handle table rows
            if trimmed.hasPrefix("|") && trimmed.hasSuffix("|") {
                // Check if this is a separator row (|---|---|)
                let isSeparator = trimmed.contains("---") || trimmed.contains(":-")
                if !isSeparator {
                    let cells = trimmed
                        .trimmingCharacters(in: CharacterSet(charactersIn: "|"))
                        .split(separator: "|")
                        .map { $0.trimmingCharacters(in: .whitespaces) }
                    tableRows.append(cells)
                }
                inTable = true
                continue
            }

            // If we were in a table and now we're not, format and output the table
            if inTable && !trimmed.hasPrefix("|") {
                result.append(contentsOf: formatTable(tableRows))
                tableRows = []
                inTable = false
            }

            // Handle horizontal rules
            if trimmed == "---" || trimmed == "***" || trimmed == "___" {
                result.append("")
                result.append("─────────────────────────")
                result.append("")
                continue
            }

            // Handle numbered lists - make them cleaner
            if let match = trimmed.range(of: #"^\d+\.\s+"#, options: .regularExpression) {
                let number = trimmed[match].trimmingCharacters(in: .whitespaces)
                let content = String(trimmed[match.upperBound...])
                result.append("")
                result.append("**\(number)** \(content)")
                continue
            }

            result.append(line)
        }

        // Handle any remaining table
        if !tableRows.isEmpty {
            result.append(contentsOf: formatTable(tableRows))
        }

        return result.joined(separator: "\n")
    }

    /// Formats a table into readable text format
    private static func formatTable(_ rows: [[String]]) -> [String] {
        guard !rows.isEmpty else { return [] }

        var result: [String] = [""]

        // Check if first row looks like a header
        let hasHeader = rows.count > 1

        for (index, row) in rows.enumerated() {
            if index == 0 && hasHeader {
                // Format header row with visual emphasis
                let headerText = row.joined(separator: "  │  ")
                result.append("┌─────────────────────────────────────────┐")
                result.append("  **\(headerText)**")
                result.append("└─────────────────────────────────────────┘")
            } else {
                // Format data rows with bullet points for better readability
                if row.count >= 2 {
                    // Two-column format: "▸ Key: Value"
                    let key = row[0]
                    let value = row.dropFirst().joined(separator: " — ")
                    result.append("  ▸ **\(key):**  \(value)")
                } else {
                    result.append("  ▸ \(row.joined(separator: "  │  "))")
                }
            }
        }

        result.append("")
        return result
    }
}
