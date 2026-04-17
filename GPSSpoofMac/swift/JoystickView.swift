import SwiftUI

struct JoystickView: View {
    var onVelocityChange: (CGVector) -> Void

    private let baseSize: CGFloat = 140
    private let knobSize: CGFloat = 52
    private var maxRadius: CGFloat { (baseSize - knobSize) / 2 }

    // Knob position is the gesture state itself — SwiftUI resets it to .zero
    // automatically when the drag ends, regardless of where the mouse is released.
    @GestureState private var dragOffset: CGSize = .zero

    var body: some View {
        ZStack {
            // Base circle — gesture lives here so it's on a stable, non-moving view
            Circle()
                .fill(Color(NSColor.controlBackgroundColor))
                .frame(width: baseSize, height: baseSize)
                .overlay(Circle().stroke(Color(NSColor.separatorColor), lineWidth: 1.5))
                .shadow(color: .black.opacity(0.1), radius: 4)
                .gesture(
                    DragGesture(minimumDistance: 0, coordinateSpace: .local)
                        .updating($dragOffset) { value, state, _ in
                            // value.location is the absolute finger/cursor position
                            // within the base circle's local coordinate space
                            let dx = value.location.x - baseSize / 2
                            let dy = value.location.y - baseSize / 2
                            let dist = hypot(dx, dy)
                            if dist <= maxRadius {
                                state = CGSize(width: dx, height: dy)
                            } else {
                                let angle = atan2(dy, dx)
                                state = CGSize(
                                    width:  cos(angle) * maxRadius,
                                    height: sin(angle) * maxRadius
                                )
                            }
                        }
                        .onChanged { value in
                            let dx = value.location.x - baseSize / 2
                            let dy = value.location.y - baseSize / 2
                            let dist = hypot(dx, dy)
                            let nx: Double
                            let ny: Double
                            if dist <= maxRadius {
                                nx = Double(dx / maxRadius)
                                ny = Double(dy / maxRadius)
                            } else {
                                let angle = atan2(dy, dx)
                                nx = Double(cos(angle))
                                ny = Double(sin(angle))
                            }
                            onVelocityChange(CGVector(dx: nx, dy: ny))
                        }
                        .onEnded { _ in
                            onVelocityChange(.zero)
                        }
                )

            // Cardinal labels
            let arrows = ["N", "S", "W", "E"]
            let positions: [(CGFloat, CGFloat)] = [(0, -52), (0, 52), (-52, 0), (52, 0)]
            ForEach(0..<4, id: \.self) { i in
                Text(arrows[i])
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .offset(x: positions[i].0, y: positions[i].1)
            }

            // Center crosshair
            Path { path in
                path.move(to: CGPoint(x: baseSize / 2 - 10, y: baseSize / 2))
                path.addLine(to: CGPoint(x: baseSize / 2 + 10, y: baseSize / 2))
                path.move(to: CGPoint(x: baseSize / 2, y: baseSize / 2 - 10))
                path.addLine(to: CGPoint(x: baseSize / 2, y: baseSize / 2 + 10))
            }
            .stroke(Color(NSColor.separatorColor), lineWidth: 1)
            .frame(width: baseSize, height: baseSize)

            // Knob — purely visual, no gesture of its own
            Circle()
                .fill(Color.accentColor)
                .frame(width: knobSize, height: knobSize)
                .shadow(color: .black.opacity(0.2), radius: 4, y: 2)
                .offset(dragOffset)
                // No animation during drag (tracks pointer directly);
                // spring animation only when dragOffset resets to .zero on release.
                .animation(dragOffset == .zero ? .spring(duration: 0.2) : nil, value: dragOffset)
                .allowsHitTesting(false) // clicks pass through to the base circle
        }
        .frame(width: baseSize, height: baseSize)
    }
}
