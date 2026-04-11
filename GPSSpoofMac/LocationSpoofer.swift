import Foundation
import CoreLocation
import Combine

class LocationSpoofer: ObservableObject {

    @Published var coordinate = CLLocationCoordinate2D(latitude: 37.7749, longitude: -122.4194)
    @Published var speed: Double = 8.0
    @Published var isRunning = false
    @Published var statusMessage = "Connect your iPhone via USB, then tap Jump or use the joystick"

    private var joystickVector: CGVector = .zero
    private var timer: Timer?
    private let updateInterval = 1.0 / 10.0 // 10fps to avoid spamming device

    // MARK: - Public

    func jumpTo(latitude: Double, longitude: Double) {
        let lat = max(-90, min(90, latitude))
        let lon = max(-180, min(180, longitude))
        coordinate = CLLocationCoordinate2D(latitude: lat, longitude: lon)
        sendToDevice(lat: lat, lon: lon)
    }

    func updateJoystick(_ vector: CGVector) {
        joystickVector = vector
        if vector.dx == 0 && vector.dy == 0 {
            stopTimer()
        } else {
            startTimer()
        }
    }

    func stop() {
        stopTimer()
        joystickVector = .zero
        isRunning = false
        statusMessage = "Stopped — disconnect USB to restore real GPS"
    }

    // MARK: - Private

    private func sendToDevice(lat: Double, lon: Double) {
        guard let url = URL(string: "http://localhost:8765/jump") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONSerialization.data(withJSONObject: ["lat": lat, "lon": lon])

        URLSession.shared.dataTask(with: request) { [weak self] data, response, error in
            DispatchQueue.main.async {
                if let error = error {
                    self?.statusMessage = "⚠️ Server unreachable: \(error.localizedDescription)"
                    self?.isRunning = false
                } else {
                    self?.statusMessage = "📍 \(String(format: "%.5f", lat)), \(String(format: "%.5f", lon))"
                    self?.isRunning = true
                }
            }
        }.resume()
    }

    private func startTimer() {
        guard timer == nil else { return }
        timer = Timer.scheduledTimer(withTimeInterval: updateInterval, repeats: true) { [weak self] _ in
            self?.tick()
        }
    }

    private func stopTimer() {
        timer?.invalidate()
        timer = nil
    }

    private func tick() {
        let metersPerTick = speed * updateInterval
        let latDeg = 111_000.0
        let lonDeg = 111_000.0 * cos(coordinate.latitude * .pi / 180)

        let latDelta = Double(-joystickVector.dy) * metersPerTick / latDeg
        let lonDelta = Double(joystickVector.dx) * metersPerTick / lonDeg

        DispatchQueue.main.async {
            self.coordinate.latitude  += latDelta
            self.coordinate.longitude += lonDelta
            self.sendToDevice(lat: self.coordinate.latitude, lon: self.coordinate.longitude)
        }
    }
}
