import Vision
import AppKit

guard CommandLine.arguments.count > 1 else {
    fputs("Usage: ocr <image-path>\n", stderr)
    exit(1)
}

let path = CommandLine.arguments[1]

guard let image = NSImage(contentsOfFile: path),
      let tiffData = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiffData),
      let cgImage = bitmap.cgImage else {
    // Silently exit for unreadable images
    exit(0)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true

let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

do {
    try handler.perform([request])
} catch {
    exit(0)
}

let text = request.results?
    .compactMap { $0.topCandidates(1).first?.string }
    .joined(separator: "\n") ?? ""

print(text)
