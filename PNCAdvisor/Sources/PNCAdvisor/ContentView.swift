import SwiftUI

/// Main content view that manages the full Foundry experience
struct ContentView: View {
    @State private var advisor = AdvisorViewModel()
    @State private var appState = AppState()
    @State private var isChatOpen: Bool = false
    @State private var isChatExpanded: Bool = false

    var body: some View {
        ZStack {
            if advisor.isLoading {
                // Model loading screen
                ModelLoadingView(
                    status: advisor.loadingStatus,
                    errorMessage: advisor.errorMessage,
                    onRetry: {
                        Task {
                            await advisor.loadModel()
                        }
                    }
                )
            } else if !advisor.modelLoaded {
                // Initial state - prompt to load model
                initialLoadPrompt
            } else {
                // Main Foundry Interface
                mainInterface
            }
        }
        .frame(minWidth: 1000, minHeight: 700)
        .onAppear {
            // Automatically start loading the model
            Task {
                await advisor.loadModel()
            }
        }
    }

    // MARK: - Main Interface

    private var mainInterface: some View {
        GeometryReader { geometry in
            ZStack(alignment: .topTrailing) {  // Changed to topTrailing for upper right
                // Foundry View (main content)
                FoundryView(
                    appState: appState,
                    advisor: advisor,
                    onOpenChat: { artifact in
                        isChatOpen = true

                        // If an artifact is provided, auto-send a relevant prompt
                        if let artifact = artifact {
                            Task {
                                await initiateFoundrySolution(for: artifact)
                            }
                        }
                    }
                )

                // Chat Widget (upper right corner)
                if isChatOpen {
                    chatWidget(in: geometry)
                }
            }
        }
    }

    // MARK: - Foundry Solution

    private func initiateFoundrySolution(for artifact: AnalysisArtifact) async {
        // Build a contextual prompt based on the analysis
        let prompt = """
        Based on the \(artifact.styleName) analysis you provided, I'd like to initiate the Foundry Solution.

        Here's the analysis context:
        \(artifact.content.prefix(500))...

        Please provide specific actionable steps to implement the recommended strategy, including:
        1. Immediate actions I can take
        2. PNC products or services that would help
        3. Timeline and milestones
        4. Key metrics to track success
        """

        await advisor.sendMessage(prompt)
    }

    // MARK: - Chat Widget

    private func chatWidget(in geometry: GeometryProxy) -> some View {
        // Calculate expanded size to fill most of the screen
        let expandedWidth = geometry.size.width - 80  // 40px padding on each side
        let expandedHeight = geometry.size.height - 100  // Leave space for top bar

        return VStack(spacing: 0) {
            // Chat Header
            HStack {
                HStack(spacing: 8) {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 8, height: 8)
                    Text("ADVISOR: SARAH V.")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundColor(PNCTheme.Colors.white)
                        .kerning(1)
                }

                Spacer()

                // Expand/Collapse Button
                Button(action: { isChatExpanded.toggle() }) {
                    Image(systemName: isChatExpanded ? "arrow.down.right.and.arrow.up.left" : "arrow.up.left.and.arrow.down.right")
                        .font(.system(size: 12))
                        .foregroundColor(PNCTheme.Colors.white.opacity(0.8))
                        .frame(width: 24, height: 24)
                }
                .buttonStyle(.plain)
                .pncHoverEffect(showBorder: false, scale: 1.1)

                // Close Button
                Button(action: { isChatOpen = false }) {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(PNCTheme.Colors.white.opacity(0.8))
                        .frame(width: 24, height: 24)
                }
                .buttonStyle(.plain)
                .pncHoverEffect(showBorder: false, scale: 1.1)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(PNCTheme.Colors.darkGrey)

            // Chat Content
            ChatView(viewModel: advisor)
        }
        .frame(
            width: isChatExpanded ? expandedWidth : 380,
            height: isChatExpanded ? expandedHeight : 450
        )
        .background(PNCTheme.Colors.white)
        .shadow(color: .black.opacity(0.2), radius: isChatExpanded ? 20 : 12, y: 4)
        .padding(.top, isChatExpanded ? 50 : 70)
        .padding(.trailing, isChatExpanded ? 40 : 20)
        .animation(.easeInOut(duration: 0.25), value: isChatExpanded)
    }

    // MARK: - Initial Load Prompt

    private var initialLoadPrompt: some View {
        ZStack {
            PNCTheme.Colors.lightGrey
                .ignoresSafeArea()

            VStack(spacing: PNCTheme.Spacing.xl) {
                VStack(spacing: PNCTheme.Spacing.sm) {
                    Text("PNC")
                        .font(.system(size: 48, weight: .black))
                        .foregroundColor(PNCTheme.Colors.darkGrey)

                    Text("STRATEGIC FOUNDRY")
                        .font(PNCTheme.Typography.caption)
                        .foregroundColor(PNCTheme.Colors.orange)
                        .kerning(2)
                }

                VStack(spacing: PNCTheme.Spacing.md) {
                    Text("Local AI Advisor Ready")
                        .font(PNCTheme.Typography.headline)
                        .foregroundColor(PNCTheme.Colors.darkGrey)

                    Text("The 4-bit quantized PNC Strategic Advisor model\nwill run entirely on your device.")
                        .font(PNCTheme.Typography.body)
                        .foregroundColor(PNCTheme.Colors.textSecondary)
                        .multilineTextAlignment(.center)
                }

                Button(action: {
                    Task {
                        await advisor.loadModel()
                    }
                }) {
                    HStack {
                        Image(systemName: "cpu")
                        Text("INITIALIZE ADVISOR")
                    }
                }
                .buttonStyle(PNCOrangeButtonStyle())
                .pncHoverEffect(scale: 1.03)
            }
        }
    }
}

#Preview {
    ContentView()
}
