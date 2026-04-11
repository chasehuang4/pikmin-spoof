import SwiftUI

struct JoystickView: View {
    var onVelocityChange: (CGVector) -> Void

    private let baseSize: CGFloat = 140
    private let knobSize: CGFloat = 52
    private var maxRadius: CGFloat { (baseSize - knobSize) / 2 }

    @State private var knobOffset: CGSize = .zero

    var body: some View {
        ZStack {
            // Base
            Circle()
                .fill(Color(NSColor.controlBackgroundColor))
                .frame(width: baseSize, height: baseSize)
                .overlay(Circle().stroke(Color(NSColor.separatorColor), lineWidth: 1.5))
                .shadow(color: .black.opacity(0.1), radius: 4)

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

            // Knob
            Circle()
                .fill(Color.accentColor)
                .frame(width: knobSize, height: knobSize)
                .shadow(color: .black.opacity(0.2), radius: 4, y: 2)
                .offset(knobOffset)
                .simultaneousGesture(
                    DragGesture(minimumDistance: 0)
                        .onChanged { value in
                            let x = value.translation.width
                            let y = value.translation.height
                            let dist = hypot(x, y)

                            if dist <= maxRadius {
                                knobOffset = CGSize(width: x, height: y)
                            } else {
                                let angle = atan2(y, x)
                                knobOffset = CGSize(
                                    width: cos(angle) * maxRadius,
                                    height: sin(angle) * maxRadius
                                )
                            }

                            let nx = Double(knobOffset.width / maxRadius)
                            let ny = Double(knobOffset.height / maxRadius)
                            onVelocityChange(CGVector(dx: nx, dy: ny))
                        }
                        .onEnded { _ in
                            withAnimation(.spring(duration: 0.2)) {
                                knobOffset = .zero
                            }
                            onVelocityChange(.zero)
                        }
                )
        }
        .frame(width: baseSize, height: baseSize)
    }
}
