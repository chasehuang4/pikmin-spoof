import SwiftUI

@main
struct GPSSpoofApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowStyle(.titleBar)
        .windowToolbarStyle(.unified)
        .defaultSize(width: 900, height: 620)
        .commands {
            CommandGroup(replacing: .newItem) {}
        }
    }
}
