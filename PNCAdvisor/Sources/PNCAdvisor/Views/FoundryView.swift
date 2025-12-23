import SwiftUI

/// Main Foundry view with analysis input, cards, and integrated features
struct FoundryView: View {
    @Bindable var appState: AppState
    @Bindable var advisor: AdvisorViewModel
    let onOpenChat: (AnalysisArtifact?) -> Void

    @State private var inputValue: String = ""
    @State private var showStatModal: Bool = false
    @State private var showNotificationModal: Bool = false
    @State private var isInputHovered: Bool = false
    @State private var isSubmitHovered: Bool = false

    var body: some View {
        ZStack {
            // Main Content
            mainContent

            // Profile Sidebar Overlay (from LEFT)
            if appState.isProfileSidebarOpen {
                sidebarOverlay
            }

            // Loading Overlay for Stat Analysis
            if appState.isLoadingStatAnalysis && !showStatModal {
                statAnalysisLoadingOverlay
            }

            // Stat Analysis Modal
            if showStatModal, let stat = appState.selectedStat {
                modalOverlay {
                    StrategicIntelligenceModal(
                        title: "\(stat.label) Analysis",
                        subtitle: "Deep-trace analysis of your \(stat.value) position",
                        analysis: $appState.statAnalysis,
                        isLoading: appState.isLoadingStatAnalysis,
                        actionButtonTitle: "INITIATE FOUNDRY SOLUTION",
                        onAction: {
                            showStatModal = false
                            onOpenChat(nil)
                        },
                        onDismiss: { showStatModal = false }
                    )
                }
            }
        }
    }

    // MARK: - Stat Analysis Loading Overlay

    private var statAnalysisLoadingOverlay: some View {
        ZStack {
            // Dimmed background that blocks interaction
            Color.black.opacity(0.6)
                .ignoresSafeArea()

            // Loading Card
            VStack(spacing: PNCTheme.Spacing.lg) {
                // Animated logo/spinner
                ZStack {
                    // Outer rotating ring
                    Circle()
                        .stroke(PNCTheme.Colors.orange.opacity(0.3), lineWidth: 4)
                        .frame(width: 80, height: 80)

                    Circle()
                        .trim(from: 0, to: 0.3)
                        .stroke(PNCTheme.Colors.orange, style: StrokeStyle(lineWidth: 4, lineCap: .round))
                        .frame(width: 80, height: 80)
                        .rotationEffect(Angle(degrees: loadingRotation))

                    // Inner icon
                    Image(systemName: "chart.line.uptrend.xyaxis")
                        .font(.system(size: 28, weight: .medium))
                        .foregroundColor(PNCTheme.Colors.orange)
                        .scaleEffect(pulseScale)
                }

                VStack(spacing: PNCTheme.Spacing.sm) {
                    Text("ANALYZING STRATEGIC METRIC")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(PNCTheme.Colors.orange)
                        .kerning(2)

                    if let stat = appState.selectedStat {
                        Text(stat.label)
                            .font(.system(size: 18, weight: .bold))
                            .foregroundColor(.white)
                    }

                    Text("Accessing Global Map traces...")
                        .font(.system(size: 12))
                        .foregroundColor(.white.opacity(0.7))
                }

                // Animated progress bar
                GeometryReader { geo in
                    ZStack(alignment: .leading) {
                        Rectangle()
                            .fill(Color.white.opacity(0.2))
                            .frame(height: 3)

                        Rectangle()
                            .fill(PNCTheme.Colors.orange)
                            .frame(width: geo.size.width * progressWidth, height: 3)
                    }
                }
                .frame(width: 200, height: 3)
            }
            .padding(PNCTheme.Spacing.xl)
            .background(
                RoundedRectangle(cornerRadius: 4)
                    .fill(PNCTheme.Colors.darkGrey)
                    .shadow(color: .black.opacity(0.3), radius: 20)
            )
        }
        .onAppear {
            startLoadingAnimations()
        }
    }

    // MARK: - Loading Animation State

    @State private var loadingRotation: Double = 0
    @State private var pulseScale: CGFloat = 1.0
    @State private var progressWidth: CGFloat = 0

    private func startLoadingAnimations() {
        // Rotation animation
        withAnimation(.linear(duration: 1.0).repeatForever(autoreverses: false)) {
            loadingRotation = 360
        }

        // Pulse animation
        withAnimation(.easeInOut(duration: 0.8).repeatForever(autoreverses: true)) {
            pulseScale = 1.15
        }

        // Progress bar animation
        withAnimation(.easeInOut(duration: 2.0).repeatForever(autoreverses: true)) {
            progressWidth = 1.0
        }
    }

    // MARK: - Main Content

    private var mainContent: some View {
        ZStack {
            // Consistent dotted background throughout all screens
            DottedBackground()
                .ignoresSafeArea()

            if let session = appState.currentSession {
                // Show analysis cards
                VStack(spacing: 0) {
                    topBar
                    AnalysisCardsView(
                        session: session,
                        focusedIndex: $appState.focusedArtifactIndex,
                        onCardAction: handleCardAction
                    )
                    .frame(maxHeight: .infinity)
                    inputBar
                }
            } else {
                // Show home view
                VStack(spacing: 0) {
                    topBar
                    homeView
                    inputBar
                }
            }
        }
    }

    // MARK: - Top Bar

    private var topBar: some View {
        HStack {
            // Profile Button with Badge (LEFT side)
            Button(action: { appState.isProfileSidebarOpen.toggle() }) {
                ZStack(alignment: .topTrailing) {
                    ZStack {
                        Circle()
                            .stroke(PNCTheme.Colors.darkGrey, lineWidth: 2)
                            .frame(width: 44, height: 44)

                        Image(systemName: "person")
                            .font(.system(size: 18, weight: .medium))
                            .foregroundColor(PNCTheme.Colors.darkGrey)
                    }

                    if appState.unreadNotificationCount > 0 {
                        Text("\(appState.unreadNotificationCount)")
                            .font(.system(size: 10, weight: .bold))
                            .foregroundColor(.white)
                            .frame(width: 18, height: 18)
                            .background(PNCTheme.Colors.orange)
                            .clipShape(Circle())
                            .offset(x: 4, y: -4)
                    }
                }
            }
            .buttonStyle(.plain)
            .pncCircleHoverEffect()

            Spacer()

            // Advisor Button (RIGHT side)
            Button(action: { onOpenChat(nil) }) {
                HStack(spacing: 8) {
                    Text("ADVISOR: SARAH V.")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(PNCTheme.Colors.white)
                        .kerning(1)

                    Image(systemName: "plus")
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(PNCTheme.Colors.white)
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(PNCTheme.Colors.darkGrey)
            }
            .buttonStyle(.plain)
            .pncHoverEffect()
        }
        .padding(.horizontal, 24)
        .padding(.vertical, 16)
    }

    // MARK: - Home View

    private var homeView: some View {
        VStack(spacing: 0) {
            Spacer()

            VStack(spacing: 24) {
                // Tagline
                Text("BRILLIANTLY BORING SINCE 1865")
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(PNCTheme.Colors.orange)
                    .kerning(3)

                // Main Title
                HStack(spacing: 12) {
                    Text("STRATEGIC")
                        .font(.system(size: 56, weight: .black))
                        .foregroundColor(PNCTheme.Colors.darkGrey)

                    Text("FOUNDRY")
                        .font(.system(size: 56, weight: .black))
                        .foregroundColor(PNCTheme.Colors.orange)
                }

                // Subtitle with dots
                HStack(spacing: 8) {
                    Text("PNC STRATEGIC FOUNDRY ADVISOR")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(PNCTheme.Colors.darkGrey)
                        .kerning(2)

                    Circle()
                        .fill(PNCTheme.Colors.orange)
                        .frame(width: 4, height: 4)
                }

                // Description
                Text("Unique non-obvious insights for the middle market.")
                    .font(.system(size: 16))
                    .foregroundColor(PNCTheme.Colors.textSecondary)
                    .padding(.top, 8)
            }

            Spacer()
                .frame(height: 40)

            // Recent Strategic Inquiries
            recentInquiriesSection

            Spacer()
        }
        .padding(.horizontal, 40)
    }

    // MARK: - Recent Inquiries Section

    private var recentInquiriesSection: some View {
        VStack(alignment: .center, spacing: 12) {
            Text("RECENT STRATEGIC INQUIRIES")
                .font(.system(size: 9, weight: .bold))
                .foregroundColor(PNCTheme.Colors.textSecondary)
                .kerning(2)

            VStack(spacing: 4) {
                // Show placeholder prompts as recent inquiries if no sessions
                let inquiries = appState.recentSessions.isEmpty
                    ? appState.placeholderPrompts.prefix(3).map { ($0, UUID().uuidString) }
                    : appState.recentSessions.prefix(3).map { ($0.prompt, $0.id) }

                ForEach(Array(inquiries), id: \.1) { prompt, id in
                    RecentInquiryRow(prompt: prompt) {
                        if appState.recentSessions.isEmpty {
                            // Use as input if no real sessions
                            inputValue = prompt
                        } else if let index = appState.recentSessions.firstIndex(where: { $0.id == id }) {
                            appState.loadSession(at: index)
                        }
                    }
                }
            }
            .frame(maxWidth: 460)
        }
    }

    // MARK: - Input Bar

    private var inputBar: some View {
        VStack(spacing: 0) {
            // Synthesizing indicator
            if appState.isAnalyzing {
                HStack {
                    ProgressView()
                        .scaleEffect(0.8)
                        .tint(PNCTheme.Colors.orange)
                    Text("Synthesizing strategic analysis...")
                        .font(.system(size: 12))
                        .foregroundColor(PNCTheme.Colors.textSecondary)
                }
                .padding(.vertical, 12)
                .frame(maxWidth: .infinity)
                .background(Color.white.opacity(0.9))
            }

            // Input Field with optional Home Button
            HStack(spacing: 12) {
                // Home Button (only shows when not on home screen)
                if appState.currentSession != nil {
                    Button(action: { appState.goHome() }) {
                        Image(systemName: "house.fill")
                            .font(.system(size: 16, weight: .medium))
                            .foregroundColor(PNCTheme.Colors.darkGrey)
                            .frame(width: 48, height: 48)
                            .background(Color.white)
                            .overlay(
                                Rectangle()
                                    .stroke(PNCTheme.Colors.darkGrey.opacity(0.2), lineWidth: 1)
                            )
                    }
                    .buttonStyle(.plain)
                    .pncHoverEffect()
                }

                // Input Field
                HStack(spacing: 0) {
                    TextField(appState.currentPlaceholder, text: $inputValue)
                        .textFieldStyle(.plain)
                        .font(.system(size: 15))
                        .foregroundColor(PNCTheme.Colors.darkGrey)
                        .padding(.horizontal, 20)
                        .padding(.vertical, 16)
                        .onSubmit {
                            submitQuery()
                        }

                    // Submit Button
                    let hasInput = !inputValue.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                    Button(action: submitQuery) {
                        Image(systemName: "chevron.up")
                            .font(.system(size: 14, weight: .bold))
                            .foregroundColor(.white)
                            .frame(width: 48, height: 48)
                            .background(hasInput ? PNCTheme.Colors.orange : PNCTheme.Colors.darkGrey)
                    }
                    .buttonStyle(.plain)
                    .disabled(!hasInput || appState.isAnalyzing)
                    .scaleEffect(isSubmitHovered ? 1.08 : 1.0)
                    .animation(.easeInOut(duration: 0.15), value: isSubmitHovered)
                    .onHover { hovering in
                        isSubmitHovered = hovering
                    }
                }
                .background(Color.white)
                .overlay(
                    Rectangle()
                        .stroke(isInputHovered ? PNCTheme.Colors.orange : PNCTheme.Colors.darkGrey.opacity(0.2), lineWidth: isInputHovered ? 2 : 1)
                )
                .scaleEffect(isInputHovered ? 1.01 : 1.0)
                .animation(.easeInOut(duration: 0.15), value: isInputHovered)
                .onHover { hovering in
                    isInputHovered = hovering
                }
            }
            .padding(.horizontal, 200)
            .padding(.bottom, 40)
        }
    }

    // MARK: - Sidebar Overlay (FROM LEFT)

    private var sidebarOverlay: some View {
        ZStack(alignment: .leading) {  // Changed to .leading for left side
            // Dimming background
            Color.black.opacity(0.3)
                .ignoresSafeArea()
                .onTapGesture {
                    appState.isProfileSidebarOpen = false
                }

            // Sidebar (from left)
            ProfileSidebar(
                profile: appState.profile,
                notifications: appState.notifications,
                aiMode: Bindable(appState).aiMode,
                onStatTapped: { stat in
                    appState.isProfileSidebarOpen = false
                    // Show loading overlay immediately, then transition to modal
                    Task {
                        await appState.generateStatAnalysis(for: stat, using: advisor)
                        // Small delay for smooth transition from loading to modal
                        try? await Task.sleep(nanoseconds: 300_000_000)
                        showStatModal = true
                    }
                },
                onNotificationTapped: { notification in
                    appState.markNotificationAsRead(notification)
                    appState.selectedNotification = notification
                },
                onClose: {
                    appState.isProfileSidebarOpen = false
                }
            )
            .transition(.move(edge: .leading))  // Changed to .leading
        }
        .animation(.easeInOut(duration: 0.3), value: appState.isProfileSidebarOpen)
    }

    // MARK: - Modal Overlay

    private func modalOverlay<Content: View>(@ViewBuilder content: () -> Content) -> some View {
        ZStack {
            Color.black.opacity(0.5)
                .ignoresSafeArea()
                .onTapGesture {
                    showStatModal = false
                    showNotificationModal = false
                }

            content()
        }
    }

    // MARK: - Actions

    private func submitQuery() {
        let query = inputValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else { return }

        inputValue = ""
        Task {
            await appState.startAnalysis(prompt: query, using: advisor)
        }
    }

    private func handleCardAction(_ artifact: AnalysisArtifact, _ action: String) {
        if action == "FOUNDRY_SOLUTION" {
            onOpenChat(artifact)
        }
    }
}

// MARK: - Recent Inquiry Row

struct RecentInquiryRow: View {
    let prompt: String
    let onTap: () -> Void

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 0) {
                Rectangle()
                    .fill(PNCTheme.Colors.orange)
                    .frame(width: 3)

                Text(prompt)
                    .font(.system(size: 13))
                    .foregroundColor(PNCTheme.Colors.darkGrey)
                    .lineLimit(1)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.leading, 12)
                    .padding(.trailing, 16)
            }
            .frame(height: 44)
            .background(Color.white)
        }
        .buttonStyle(.plain)
        .pncHoverEffect(scale: 1.01)
    }
}

// MARK: - Preview

#Preview {
    FoundryView(
        appState: AppState(),
        advisor: AdvisorViewModel(),
        onOpenChat: { _ in }
    )
    .frame(width: 1200, height: 800)
}
