import SwiftUI
import MapKit

struct ContentView: View {
    @StateObject private var spoofer = LocationSpoofer()

    @State private var latText = "37.7749"
    @State private var lonText = "-122.4194"
    @State private var showError = false
    @State private var mapRegion = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.7749, longitude: -122.4194),
        span: MKCoordinateSpan(latitudeDelta: 0.005, longitudeDelta: 0.005)
    )
    @State private var isDraggingPin = false
    @State private var pinDragPosition: CGPoint = .zero

    var body: some View {
        HStack(spacing: 0) {

            // MARK: Left Panel — Controls
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {

                    // Title
                    HStack {
                        Image(systemName: "location.fill")
                            .foregroundStyle(.accent)
                        Text("GPS Spoof")
                            .font(.title2.bold())
                    }

                    // Status bar
                    HStack(spacing: 6) {
                        Circle()
                            .fill(spoofer.isRunning ? Color.green : Color.red)
                            .frame(width: 8, height: 8)
                        Text(spoofer.statusMessage)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color(NSColor.controlBackgroundColor))
                    .clipShape(RoundedRectangle(cornerRadius: 8))

                    Divider()

                    // MARK: Coordinate Input
                    VStack(alignment: .leading, spacing: 10) {
                        Label("Jump to Coordinate", systemImage: "mappin")
                            .font(.caption.bold())
                            .foregroundStyle(.secondary)

                        HStack(spacing: 8) {
                            VStack(alignment: .leading, spacing: 2) {
                                Text("LATITUDE").font(.caption2).foregroundStyle(.secondary)
                                TextField("e.g. 37.7749", text: $latText)
                                    .textFieldStyle(.roundedBorder)
                                    .frame(width: 110)
                            }
                            VStack(alignment: .leading, spacing: 2) {
                                Text("LONGITUDE").font(.caption2).foregroundStyle(.secondary)
                                TextField("e.g. -122.4194", text: $lonText)
                                    .textFieldStyle(.roundedBorder)
                                    .frame(width: 110)
                            }
                        }

                        if showError {
                            Text("Invalid — Lat: -90…90, Lon: -180…180")
                                .font(.caption2)
                                .foregroundStyle(.red)
                        }

                        HStack(spacing: 8) {
                            Button("Jump") {
                                if let lat = Double(latText), let lon = Double(lonText),
                                   (-90...90).contains(lat), (-180...180).contains(lon) {
                                    spoofer.jumpTo(latitude: lat, longitude: lon)
                                    showError = false
                                } else {
                                    showError = true
                                }
                            }
                            .buttonStyle(.borderedProminent)
                            .keyboardShortcut(.return)

                            Button("Use Current") {
                                latText = String(format: "%.6f", spoofer.coordinate.latitude)
                                lonText = String(format: "%.6f", spoofer.coordinate.longitude)
                            }
                            .buttonStyle(.bordered)
                        }
                    }

                    Divider()

                    // MARK: Speed
                    VStack(alignment: .leading, spacing: 6) {
                        Label("Movement Speed", systemImage: "speedometer")
                            .font(.caption.bold())
                            .foregroundStyle(.secondary)

                        HStack {
                            Slider(value: $spoofer.speed, in: 1...50, step: 1)
                            Text("\(Int(spoofer.speed)) m/s")
                                .font(.caption.monospacedDigit())
                                .frame(width: 48)
                        }

                        Text("Walking ≈ 1.5 m/s · Running ≈ 3 m/s · Fast test ≈ 10+ m/s")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                    }

                    Divider()

                    // MARK: Joystick
                    VStack(alignment: .center, spacing: 8) {
                        Label("Joystick", systemImage: "gamecontroller")
                            .font(.caption.bold())
                            .foregroundStyle(.secondary)
                            .frame(maxWidth: .infinity, alignment: .leading)

                        Text("Click and drag to move")
                            .font(.caption2)
                            .foregroundStyle(.tertiary)

                        JoystickView { vector in
                            spoofer.updateJoystick(vector)
                        }
                        .frame(maxWidth: .infinity, alignment: .center)
                    }

                    Divider()

                    // MARK: Stop Button
                    Button(role: .destructive) {
                        spoofer.stop()
                    } label: {
                        Label("Stop Spoofing", systemImage: "location.slash.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.red)
                    .help("Stops sending fake location. Disconnect USB to fully restore real GPS.")
                }
                .padding(16)
            }
            .frame(width: 290)
            .background(Color(NSColor.windowBackgroundColor))

            Divider()

            // MARK: Map
            Map(coordinateRegion: $mapRegion)
                .overlay {
                    GeometryReader { geo in
                        ZStack {
                            // Double-tap layer — jump to double-clicked coordinate
                            Color.clear
                                .contentShape(Rectangle())
                                .onTapGesture(count: 2) { location in
                                    let coord = mapCoordinate(from: location, in: geo.size)
                                    spoofer.jumpTo(latitude: coord.latitude, longitude: coord.longitude)
                                }

                            // Draggable current-position pin
                            let pinPos = screenPosition(for: spoofer.coordinate, in: geo.size)
                            if pinPos.x > -30 && pinPos.x < geo.size.width + 30 &&
                               pinPos.y > -30 && pinPos.y < geo.size.height + 30 {
                                Image(systemName: "location.circle.fill")
                                    .font(.system(size: 28))
                                    .foregroundColor(.blue)
                                    .shadow(color: .black.opacity(0.3), radius: 3, x: 0, y: 2)
                                    .position(isDraggingPin ? pinDragPosition : pinPos)
                                    .gesture(
                                        DragGesture(minimumDistance: 5)
                                            .onChanged { value in
                                                isDraggingPin = true
                                                pinDragPosition = value.location
                                            }
                                            .onEnded { value in
                                                isDraggingPin = false
                                                let newCoord = mapCoordinate(from: value.location, in: geo.size)
                                                spoofer.jumpTo(latitude: newCoord.latitude, longitude: newCoord.longitude)
                                            }
                                    )
                            }
                        }
                    }
                }
                .overlay(alignment: .bottomTrailing) {
                    Text("📍 \(String(format: "%.5f", spoofer.coordinate.latitude)), \(String(format: "%.5f", spoofer.coordinate.longitude))")
                        .font(.caption.monospacedDigit())
                        .padding(6)
                        .background(.thinMaterial)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                        .padding(12)
                }
        }
        .onChange(of: spoofer.coordinate) { newCoord in
            if !isDraggingPin {
                updateMap(to: newCoord)
            }
        }
    }

    // MARK: - Helpers

    /// Convert a map coordinate to its screen position within the given size.
    private func screenPosition(for coordinate: CLLocationCoordinate2D, in size: CGSize) -> CGPoint {
        let x = ((coordinate.longitude - mapRegion.center.longitude) / mapRegion.span.longitudeDelta + 0.5) * size.width
        let y = (0.5 - (coordinate.latitude - mapRegion.center.latitude) / mapRegion.span.latitudeDelta) * size.height
        return CGPoint(x: x, y: y)
    }

    /// Convert a screen point to a map coordinate.
    private func mapCoordinate(from point: CGPoint, in size: CGSize) -> CLLocationCoordinate2D {
        let lat = mapRegion.center.latitude + mapRegion.span.latitudeDelta * (0.5 - Double(point.y / size.height))
        let lon = mapRegion.center.longitude + mapRegion.span.longitudeDelta * (Double(point.x / size.width) - 0.5)
        return CLLocationCoordinate2D(latitude: lat, longitude: lon)
    }

    private func updateMap(to coordinate: CLLocationCoordinate2D) {
        withAnimation {
            mapRegion.center = coordinate
        }
    }
}
