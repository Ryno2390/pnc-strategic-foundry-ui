import SwiftUI
import AppKit

/// Helper class to handle app activation
class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Ensure the app can become frontmost and receive keyboard input
        NSApp.setActivationPolicy(.regular)
        NSApp.activate(ignoringOtherApps: true)

        // Set the dock icon
        // Try bundle resource first, then fall back to direct file path
        if let iconURL = Bundle.main.url(forResource: "AppIcon", withExtension: "png"),
           let icon = NSImage(contentsOf: iconURL) {
            NSApp.applicationIconImage = icon
        } else if let icon = NSImage(contentsOfFile: "/Users/ryneschultz/pnc-strategic-foundry/PNC.png") {
            // Direct path fallback for development
            NSApp.applicationIconImage = icon
        }
    }

    func applicationDidBecomeActive(_ notification: Notification) {
        // Make the main window key when app becomes active
        NSApp.windows.first?.makeKeyAndOrderFront(nil)
    }
}

/// PNC Strategic Advisor - Local AI Assistant
/// Powered by MLX Swift and a 4-bit quantized Qwen 2.5 3B model
@main
struct PNCAdvisorApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .defaultSize(width: 1000, height: 700)
        .commands {
            // Custom menu commands
            CommandGroup(replacing: .newItem) {
                Button("New Chat") {
                    NotificationCenter.default.post(name: .newChat, object: nil)
                }
                .keyboardShortcut("n", modifiers: .command)
            }
        }
    }
}

// MARK: - Notification Names
extension Notification.Name {
    static let newChat = Notification.Name("newChat")
}
