import SwiftUI

@main
struct SuzanoAbertaApp: App {
    var body: some Scene {
        WindowGroup {
            WebAppView()
                .background(Color(red: 8 / 255, green: 31 / 255, blue: 51 / 255))
                .ignoresSafeArea()
        }
    }
}
