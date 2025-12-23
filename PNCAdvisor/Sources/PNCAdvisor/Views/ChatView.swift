import SwiftUI
import AppKit
import UniformTypeIdentifiers

/// Main chat interface for the PNC Strategic Advisor
struct ChatView: View {
    @Bindable var viewModel: AdvisorViewModel
    var onGoHome: (() -> Void)? = nil  // Optional, used when shown standalone

    @State private var inputText: String = ""
    @State private var attachedFiles: [URL] = []

    var body: some View {
        VStack(spacing: 0) {
            // Messages
            messagesScrollView

            // Input area
            inputArea
        }
        .background(PNCTheme.Colors.white)
    }

    // MARK: - Messages
    private var messagesScrollView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: PNCTheme.Spacing.md) {
                    ForEach(viewModel.messages) { message in
                        MessageBubble(
                            message: message,
                            isStreaming: viewModel.isGenerating && message == viewModel.messages.last
                        )
                        .id(message.id)
                    }
                }
                .padding(.vertical, PNCTheme.Spacing.lg)
            }
            .background(Color(hex: "F9F9F9"))
            .onChange(of: viewModel.messages.count) { _, _ in
                if let lastMessage = viewModel.messages.last {
                    withAnimation(.easeOut(duration: 0.3)) {
                        proxy.scrollTo(lastMessage.id, anchor: .bottom)
                    }
                }
            }
            .onChange(of: viewModel.currentResponse) { _, _ in
                if let lastMessage = viewModel.messages.last {
                    proxy.scrollTo(lastMessage.id, anchor: .bottom)
                }
            }
        }
    }

    // MARK: - Input Area
    private var inputArea: some View {
        VStack(spacing: 0) {
            // Error message if any
            if let error = viewModel.errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(PNCTheme.Colors.orange)
                    Text(error)
                        .font(PNCTheme.Typography.caption)
                        .foregroundColor(PNCTheme.Colors.textSecondary)
                    Spacer()
                    Button("Dismiss") {
                        viewModel.errorMessage = nil
                    }
                    .font(PNCTheme.Typography.caption)
                    .foregroundColor(PNCTheme.Colors.orange)
                    .buttonStyle(.plain)
                    .pncHoverEffect(showBorder: false, scale: 1.05)
                }
                .padding(PNCTheme.Spacing.md)
                .background(PNCTheme.Colors.orange.opacity(0.1))
            }

            // Attached files preview
            if !attachedFiles.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(attachedFiles, id: \.self) { url in
                            HStack(spacing: 4) {
                                Image(systemName: "doc.fill")
                                    .font(.system(size: 10))
                                    .foregroundColor(PNCTheme.Colors.orange)
                                Text(url.lastPathComponent)
                                    .font(.system(size: 11))
                                    .foregroundColor(PNCTheme.Colors.darkGrey)
                                    .lineLimit(1)
                                Button(action: {
                                    attachedFiles.removeAll { $0 == url }
                                }) {
                                    Image(systemName: "xmark.circle.fill")
                                        .font(.system(size: 12))
                                        .foregroundColor(PNCTheme.Colors.darkGrey.opacity(0.5))
                                }
                                .buttonStyle(.plain)
                                .pncHoverEffect(showBorder: false, scale: 1.15)
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.white)
                            .overlay(
                                RoundedRectangle(cornerRadius: 4)
                                    .stroke(PNCTheme.Colors.darkGrey.opacity(0.2), lineWidth: 1)
                            )
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 8)
                }
            }

            // Input field - matching main interface styling
            HStack(spacing: 0) {
                // Attachment button
                Button(action: openFilePicker) {
                    Image(systemName: "paperclip")
                        .font(.system(size: 16))
                        .foregroundColor(PNCTheme.Colors.darkGrey.opacity(0.6))
                        .frame(width: 40, height: 48)
                }
                .buttonStyle(.plain)
                .disabled(viewModel.isGenerating)
                .pncHoverEffect(showBorder: false, scale: 1.1)

                TextField("Ask the Strategic Advisor...", text: $inputText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14))
                    .foregroundColor(PNCTheme.Colors.darkGrey)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 14)
                    .disabled(viewModel.isGenerating)
                    .onSubmit {
                        sendMessage()
                    }

                // Single button that switches between Stop and Send
                if viewModel.isGenerating {
                    Button(action: {
                        viewModel.stopGeneration()
                    }) {
                        Text("STOP")
                            .font(.system(size: 11, weight: .bold))
                            .kerning(1)
                            .foregroundColor(.white)
                            .frame(width: 64, height: 48)
                            .background(PNCTheme.Colors.orange)
                    }
                    .buttonStyle(.plain)
                    .pncHoverEffect(showBorder: false, scale: 1.02)
                } else {
                    let hasContent = !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || !attachedFiles.isEmpty
                    Button(action: sendMessage) {
                        Image(systemName: "chevron.up")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                            .frame(width: 48, height: 48)
                            .background(hasContent ? PNCTheme.Colors.orange : PNCTheme.Colors.darkGrey)
                    }
                    .buttonStyle(.plain)
                    .disabled(!hasContent || viewModel.isGenerating)
                }
            }
            .background(Color.white)
            .overlay(
                Rectangle()
                    .stroke(PNCTheme.Colors.darkGrey.opacity(0.2), lineWidth: 1)
            )
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
        }
        .background(PNCTheme.Colors.white)
    }

    // MARK: - Actions
    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty || !attachedFiles.isEmpty else { return }

        // Build message with attachment info
        var messageText = text
        if !attachedFiles.isEmpty {
            let fileNames = attachedFiles.map { $0.lastPathComponent }.joined(separator: ", ")
            if messageText.isEmpty {
                messageText = "[Attached: \(fileNames)]"
            } else {
                messageText += "\n\n[Attached: \(fileNames)]"
            }
        }

        inputText = ""
        attachedFiles.removeAll()
        Task {
            await viewModel.sendMessage(messageText)
        }
    }

    private func openFilePicker() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.canChooseFiles = true
        panel.allowedContentTypes = [
            .pdf,
            .plainText,
            .spreadsheet,
            .presentation,
            .image,
            UTType(filenameExtension: "csv")!,
            UTType(filenameExtension: "xlsx")!,
            UTType(filenameExtension: "docx")!
        ]
        panel.message = "Select documents to attach"
        panel.prompt = "Attach"

        if panel.runModal() == .OK {
            attachedFiles.append(contentsOf: panel.urls)
        }
    }
}

#Preview {
    let viewModel = AdvisorViewModel()
    viewModel.modelLoaded = true
    viewModel.messages = [
        ChatMessage(role: .advisor, content: "Welcome to the PNC Strategic Foundry. How may I assist you today?"),
        ChatMessage(role: .user, content: "What are the key risks for middle-market manufacturers?"),
        ChatMessage(role: .advisor, content: "Based on our analysis, three primary risk factors warrant attention:\n\n1. Supply Chain Concentration\n2. Working Capital Pressure\n3. Labor Market Tightness")
    ]

    return ChatView(viewModel: viewModel, onGoHome: {})
        .frame(width: 800, height: 600)
}
