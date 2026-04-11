import SwiftUI
import MapKit

struct MapPin: Identifiable {
    let id = UUID()
    var coordinate: CLLocationCoordinate2D
}

struct ContentView: View {
    @StateObject private var spoofer = LocationSpoofer()

    @State private var latText = "37.7749"
    @State private var lonText = "-122.4194"
    @State private var showError = false
    @State private var mapRegion = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.7749, longitude: -122.4194),
        span: MKCoordinateSpan(latitudeDelta: 0.005, longitudeDelta: 0.005)
    )
    @State private var pins: [MapPin] = [
        MapPin(coordinate: CLLocationCoordinate2D(latitude: 37.7749, longitude: -122.4194))
    ]

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
                                    updateMap(to: spoofer.coordinate)
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
            Map(coordinateRegion: $mapRegion, annotationItems: pins) { pin in
                MapMarker(coordinate: pin.coordinate, tint: .red)
            }
            .overlay {
                GeometryReader { geo in
                    Color.clear
                        .contentShape(Rectangle())
                        .onTapGesture { location in
                            let lat = mapRegion.center.latitude
                                + mapRegion.span.latitudeDelta * (0.5 - Double(location.y / geo.size.height))
                            let lon = mapRegion.center.longitude
                                + mapRegion.span.longitudeDelta * (Double(location.x / geo.size.width) - 0.5)
                            spoofer.jumpTo(latitude: lat, longitude: lon)
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
            updateMap(to: newCoord)
        }
    }

    private func updateMap(to coordinate: CLLocationCoordinate2D) {
        pins = [MapPin(coordinate: coordinate)]
        withAnimation {
            mapRegion.center = coordinate
        }
    }
}
