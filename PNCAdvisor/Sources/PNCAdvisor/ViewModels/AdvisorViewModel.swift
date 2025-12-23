import Foundation
import SwiftUI
import MLXLLM
import MLXLMCommon
import MLX

/// PNC Strategic Advisor System Prompt
private let systemPrompt = """
You are the PNC Strategic Advisor (Sarah V.), an AI assistant representing PNC Bank's Global Intelligence Foundry. You embody the bank's "Brilliantly Boring" philosophy—providing steady, professional, and responsible guidance.

Core Principles:
- Provide comprehensive, data-rich analysis with specific numbers, percentages, and dollar amounts
- Use tables to present comparative data, metrics, and benchmarks clearly
- Structure responses with clear headers (##) for easy navigation
- Include relevant KPIs, performance metrics, and trend analysis
- When presenting options or comparisons, use formatted tables
- Focus on strategic insights that connect data points across Retail, Commercial, and Wealth
- Prioritize "Resilience" thinking—help clients anticipate and navigate challenges
- When you lack sufficient data, acknowledge limitations and decline to speculate
- Never provide irresponsible financial advice or speculative predictions without data support

Response Format Guidelines:
- Use ## headers to organize sections
- Use tables (| Column | Column |) for data presentation
- Include specific metrics with Current vs. Benchmark comparisons
- Provide actionable recommendations with timelines and expected impact
- Reference relevant PNC products/services where appropriate

You are responsible since 1865. Act accordingly.
"""

/// ViewModel for the PNC Strategic Advisor chat interface
@MainActor
@Observable
final class AdvisorViewModel {
    // MARK: - Published State
    var messages: [ChatMessage] = []
    var currentResponse: String = ""
    var isLoading: Bool = false
    var isGenerating: Bool = false
    var modelLoaded: Bool = false
    var loadingStatus: String = "Initializing..."
    var errorMessage: String?

    // MARK: - Private Properties
    private(set) var modelContainer: ModelContainer?
    private var generateTask: Task<Void, Never>?

    /// URL to the local model directory
    private let localModelURL: URL

    // MARK: - Initialization
    // Load the custom PNC Strategic Advisor model from local path
    init(modelPath: String = "/Users/ryneschultz/pnc-strategic-foundry/outputs/pnc-advisor-4bit") {
        self.localModelURL = URL(fileURLWithPath: modelPath)
    }

    // MARK: - Model Loading
    func loadModel() async {
        guard !modelLoaded else {
            print("[PNC] Model already loaded")
            return
        }

        isLoading = true
        errorMessage = nil
        loadingStatus = "Loading PNC Strategic Advisor model..."
        print("[PNC] Starting model load from local path: \(localModelURL.path)")

        do {
            // Configure MLX memory limits for efficient operation
            MLX.GPU.set(cacheLimit: 512 * 1024 * 1024)  // 512MB cache
            print("[PNC] GPU cache configured")

            loadingStatus = "Initializing model configuration..."
            print("[PNC] Using local model directory: \(localModelURL.path)")

            // Use directory initializer for local model loading
            let configuration = ModelConfiguration(
                directory: localModelURL,
                defaultPrompt: "What strategic insights can you provide?"
            )
            print("[PNC] Configuration created for local directory")

            loadingStatus = "Loading model weights (1.6GB)..."
            print("[PNC] Starting LLMModelFactory.loadContainer with local model...")

            // Load the model container from local directory
            modelContainer = try await LLMModelFactory.shared.loadContainer(
                configuration: configuration
            ) { progress in
                let percent = Int(progress.fractionCompleted * 100)
                print("[PNC] Loading progress: \(percent)%")
                Task { @MainActor in
                    self.loadingStatus = "Loading model: \(percent)%"
                }
            }

            print("[PNC] Model container loaded successfully!")
            loadingStatus = "Model ready"
            modelLoaded = true

            // Add welcome message
            messages.append(ChatMessage(
                role: .advisor,
                content: "Welcome to the PNC Strategic Foundry. I am your Strategic Advisor, Sarah V. How may I assist you today?"
            ))

        } catch {
            print("[PNC] ERROR loading model: \(error)")
            print("[PNC] Error details: \(error.localizedDescription)")
            errorMessage = "Failed to load model: \(error.localizedDescription)"
            loadingStatus = "Error loading model"
        }

        isLoading = false
        print("[PNC] Load complete. modelLoaded=\(modelLoaded), isLoading=\(isLoading)")
    }

    // MARK: - Message Handling
    func sendMessage(_ text: String) async {
        let trimmedText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedText.isEmpty, !isGenerating else { return }

        print("[PNC] Sending message: \(trimmedText.prefix(50))...")

        // Add user message
        messages.append(ChatMessage(role: .user, content: trimmedText))

        // Start generating response
        isGenerating = true
        currentResponse = ""
        errorMessage = nil

        // Add placeholder for advisor response
        let advisorMessageId = UUID()
        messages.append(ChatMessage(id: advisorMessageId, role: .advisor, content: ""))

        generateTask = Task {
            await generateResponse(for: trimmedText, messageId: advisorMessageId)
        }
    }

    private func generateResponse(for prompt: String, messageId: UUID) async {
        guard let container = modelContainer else {
            print("[PNC] ERROR: Model not loaded")
            errorMessage = "Model not loaded"
            isGenerating = false
            return
        }

        print("[PNC] Starting generation...")

        do {
            // Add repetition penalty to prevent loops
            let parameters = GenerateParameters(
                temperature: 0.7,
                topP: 0.9,
                repetitionPenalty: 1.2,
                repetitionContextSize: 64
            )

            let result = try await container.perform { context in
                print("[PNC] Preparing input...")
                // Prepare input using messages format
                let input = try await context.processor.prepare(
                    input: .init(messages: [
                        ["role": "system", "content": systemPrompt],
                        ["role": "user", "content": prompt]
                    ])
                )
                print("[PNC] Input prepared, generating...")

                // Generate with streaming callback
                return try MLXLMCommon.generate(
                    input: input,
                    parameters: parameters,
                    context: context
                ) { tokens in
                    let partial = context.tokenizer.decode(tokens: tokens)

                    Task { @MainActor in
                        self.currentResponse = partial
                        if let index = self.messages.firstIndex(where: { $0.id == messageId }) {
                            self.messages[index].content = partial
                        }
                    }

                    // Detect repetition - check if the last characters keep repeating
                    if partial.count > 50 {
                        let recentChars = String(partial.suffix(30))
                        let previousChars = String(partial.dropLast(30).suffix(30))
                        if recentChars == previousChars || detectRepeatingPattern(in: partial) {
                            print("[PNC] Repetition detected, stopping generation")
                            return .stop
                        }
                    }

                    // Stop after 2048 tokens for more detailed responses
                    return tokens.count >= 2048 ? .stop : .more
                }
            }

            print("[PNC] Generation complete: \(result.output.prefix(100))...")

            // Finalize the response
            await MainActor.run {
                if let index = messages.firstIndex(where: { $0.id == messageId }) {
                    messages[index].content = result.output
                }
                currentResponse = ""
                isGenerating = false
            }

        } catch {
            print("[PNC] Generation ERROR: \(error)")
            await MainActor.run {
                errorMessage = "Generation failed: \(error.localizedDescription)"
                // Remove the empty advisor message on error
                messages.removeAll { $0.id == messageId }
                isGenerating = false
            }
        }
    }

    // MARK: - Utilities
    func stopGeneration() {
        generateTask?.cancel()
        generateTask = nil
        isGenerating = false
    }

    func clearMessages() {
        messages.removeAll()
        // Re-add welcome message
        messages.append(ChatMessage(
            role: .advisor,
            content: "Welcome to the PNC Strategic Foundry. I am your Strategic Advisor, Sarah V. How may I assist you today?"
        ))
    }

}

// MARK: - Repetition Detection Helper (outside actor)

/// Detects if the text ends with a repeating word or phrase pattern
private func detectRepeatingPattern(in text: String) -> Bool {
    let words = text.split(separator: " ").map(String.init)
    guard words.count >= 6 else { return false }

    // Check last 6 words for repetition
    let lastWords = Array(words.suffix(6))

    // Check for same word repeated 3+ times
    let lastWord = lastWords.last ?? ""
    let repeatCount = lastWords.filter { $0.lowercased() == lastWord.lowercased() }.count
    if repeatCount >= 3 {
        return true
    }

    // Check for 2-word phrase repetition
    if words.count >= 8 {
        let phrase1 = words.suffix(2).joined(separator: " ").lowercased()
        let phrase2 = words.dropLast(2).suffix(2).joined(separator: " ").lowercased()
        let phrase3 = words.dropLast(4).suffix(2).joined(separator: " ").lowercased()
        if phrase1 == phrase2 && phrase2 == phrase3 {
            return true
        }
    }

    return false
}
