import Foundation
import SwiftUI

/// AI Processing Mode - determines where queries are processed
enum AIProcessingMode: String, CaseIterable {
    case onDevice = "On-Device"
    case onNetwork = "On-Network"

    var description: String {
        switch self {
        case .onDevice:
            return "Local MLX Model"
        case .onNetwork:
            return "PNC Cloud API"
        }
    }

    var icon: String {
        switch self {
        case .onDevice:
            return "cpu"
        case .onNetwork:
            return "cloud"
        }
    }
}

/// Central state management for the PNC Strategic Foundry app
@MainActor
@Observable
final class AppState {
    // MARK: - Profile & Products
    var profile: ExecutiveProfile = .default
    var notifications: [AppNotification] = AppNotification.defaultNotifications

    // MARK: - Analysis Sessions
    var sessions: [AnalysisSession] = []
    var currentSessionIndex: Int?
    var focusedArtifactIndex: Int?
    var isAnalyzing: Bool = false

    // MARK: - AI Processing Mode
    var aiMode: AIProcessingMode = .onDevice

    // MARK: - UI State
    var isProfileSidebarOpen: Bool = false
    var isChatExpanded: Bool = false
    var selectedStat: ProfileStat?
    var selectedNotification: AppNotification?
    var statAnalysis: String = ""
    var isLoadingStatAnalysis: Bool = false

    // MARK: - Placeholder Prompts
    let placeholderPrompts = [
        "Analyze Q3 retail spending vs commercial liquidity",
        "Compare my regional cash flow to the Global Map",
        "Identify payroll optimization opportunities",
        "Strategic overview of merchant services trends",
        "Assess treasury management for expansion",
        "Visualize sector-wide risk prevention benchmarks",
        "Draft a post-merger integration strategy",
        "Analyze supply chain resilience traces"
    ]

    var currentPromptIndex: Int = 0

    var currentPlaceholder: String {
        placeholderPrompts[currentPromptIndex]
    }

    // MARK: - Computed Properties

    var currentSession: AnalysisSession? {
        guard let index = currentSessionIndex, index < sessions.count else { return nil }
        return sessions[index]
    }

    var unreadNotificationCount: Int {
        notifications.filter { !$0.isRead }.count
    }

    var recentSessions: [AnalysisSession] {
        Array(sessions.prefix(5))
    }

    // MARK: - Actions

    func cyclePlaceholder(forward: Bool = true) {
        if forward {
            currentPromptIndex = (currentPromptIndex + 1) % placeholderPrompts.count
        } else {
            currentPromptIndex = (currentPromptIndex - 1 + placeholderPrompts.count) % placeholderPrompts.count
        }
    }

    func startAnalysis(prompt: String, using advisor: AdvisorViewModel) async {
        isAnalyzing = true
        focusedArtifactIndex = nil

        // Create new session
        var session = AnalysisSession(prompt: prompt)

        // Generate 3 analysis vectors
        let vectors = AnalysisVector.randomThree()
        session.artifacts = vectors.map { AnalysisArtifact(styleName: $0.rawValue) }

        sessions.insert(session, at: 0)
        currentSessionIndex = 0

        // Generate content for each artifact
        for (index, vector) in vectors.enumerated() {
            let analysisPrompt = buildAnalysisPrompt(userPrompt: prompt, vector: vector)

            // Update artifact status to streaming
            sessions[0].artifacts[index].status = .streaming

            // Generate analysis using the advisor
            let response = await generateAnalysis(prompt: analysisPrompt, using: advisor)

            // Update artifact with response
            sessions[0].artifacts[index].content = response
            sessions[0].artifacts[index].status = .complete
        }

        isAnalyzing = false
    }

    private func buildAnalysisPrompt(userPrompt: String, vector: AnalysisVector) -> String {
        """
        Generate a comprehensive strategic analysis from the "\(vector.rawValue)" perspective for this query: "\(userPrompt)"

        Structure your response with:

        ## Executive Summary
        (3-4 sentence strategic overview with key metrics)

        ## Key Findings
        | Finding | Impact | Priority |
        |---------|--------|----------|
        (Include 4-5 data-driven findings in table format)

        ## Performance Metrics
        | Metric | Current | Benchmark | Gap |
        |--------|---------|-----------|-----|
        (Include relevant KPIs with specific numbers)

        ## Global Map Comparison
        Detailed comparison to sector benchmarks with percentile rankings.

        ## Risk Assessment
        | Risk Factor | Probability | Impact | Mitigation |
        |-------------|-------------|--------|------------|
        (Include 3-4 key risks)

        ## Actionable Strategy
        1. Immediate actions (0-30 days)
        2. Short-term initiatives (30-90 days)
        3. Strategic objectives (90+ days)

        ## Foundry Solution
        Specific PNC products/services with projected ROI and implementation pathway.

        Provide detailed, data-rich analysis with specific numbers, percentages, and dollar amounts. Use tables to present comparative data clearly.
        """
    }

    private func generateAnalysis(prompt: String, using advisor: AdvisorViewModel) async -> String {
        // Use the advisor's model to generate analysis
        guard let container = advisor.modelContainer else {
            return "Error: Model not available"
        }

        do {
            let result = try await container.perform { context in
                let input = try await context.processor.prepare(
                    input: .init(messages: [
                        ["role": "system", "content": "You are a strategic financial analyst for PNC Bank's Global Intelligence Foundry. Provide concise, data-driven analysis."],
                        ["role": "user", "content": prompt]
                    ])
                )

                return try MLXLMCommon.generate(
                    input: input,
                    parameters: GenerateParameters(temperature: 0.7),
                    context: context
                ) { tokens in
                    // Increased to 1024 tokens for more detailed analysis
                    return tokens.count >= 1024 ? .stop : .more
                }
            }
            return result.output
        } catch {
            return "Analysis generation failed: \(error.localizedDescription)"
        }
    }

    func generateStatAnalysis(for stat: ProfileStat, using advisor: AdvisorViewModel) async {
        selectedStat = stat
        isLoadingStatAnalysis = true
        statAnalysis = ""

        let prompt = """
        Provide a comprehensive strategic intelligence analysis for our client's \(stat.label) metric showing \(stat.value).

        Include:

        ## Executive Summary
        Strategic overview of this metric's implications for business performance and growth trajectory.

        ## Current Position Analysis
        | Metric | Value | Percentile | Trend |
        |--------|-------|------------|-------|
        (Detailed breakdown with specific data points)

        ## Global Map Comparison
        | Benchmark | Client | Sector Avg | Top Quartile |
        |-----------|--------|------------|--------------|
        (How this compares to similar middle-market industrial clients with specific percentages)

        ## Trend Analysis
        Historical performance and projected trajectory with key inflection points.

        ## Risk & Opportunity Assessment
        | Factor | Type | Impact | Probability |
        |--------|------|--------|-------------|
        (Key risks and opportunities with quantified impact)

        ## Recommended Actions
        | Priority | Action | Expected Impact | Timeline |
        |----------|--------|-----------------|----------|
        (Specific steps to enhance this metric with projected outcomes)

        ## PNC Solutions
        Relevant PNC products and services that could optimize this metric, with estimated ROI.

        Provide detailed, data-rich analysis with specific numbers, percentages, and dollar amounts. Use tables to present comparative data clearly.
        """

        guard let container = advisor.modelContainer else {
            statAnalysis = "Error: Model not available"
            isLoadingStatAnalysis = false
            return
        }

        do {
            let result = try await container.perform { context in
                let input = try await context.processor.prepare(
                    input: .init(messages: [
                        ["role": "system", "content": "You are Sarah V., PNC Strategic Advisor. Provide detailed strategic analysis."],
                        ["role": "user", "content": prompt]
                    ])
                )

                return try MLXLMCommon.generate(
                    input: input,
                    parameters: GenerateParameters(temperature: 0.7),
                    context: context
                ) { tokens in
                    // Increased to 1024 tokens for more detailed analysis
                    return tokens.count >= 1024 ? .stop : .more
                }
            }
            statAnalysis = result.output
        } catch {
            statAnalysis = "Analysis failed: \(error.localizedDescription)"
        }

        isLoadingStatAnalysis = false
    }

    func markNotificationAsRead(_ notification: AppNotification) {
        if let index = notifications.firstIndex(where: { $0.id == notification.id }) {
            notifications[index].isRead = true
        }
    }

    func enrollProduct(name: String, value: String) {
        let product = EnrolledProduct(
            id: UUID().uuidString,
            name: name,
            value: value,
            status: .active,
            enrolledDate: Date()
        )
        profile.enrolledProducts.append(product)

        // Add approval notification
        let notification = AppNotification(
            id: UUID().uuidString,
            title: "Product Enrolled",
            message: "\(name) has been successfully activated for your account.",
            type: .approval,
            isRead: false,
            timestamp: Date()
        )
        notifications.insert(notification, at: 0)
    }

    func loadSession(at index: Int) {
        guard index < sessions.count else { return }
        currentSessionIndex = index
        focusedArtifactIndex = nil
    }

    func goHome() {
        currentSessionIndex = nil
        focusedArtifactIndex = nil
    }
}

// MARK: - MLXLMCommon Import

import MLXLMCommon
