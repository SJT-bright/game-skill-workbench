// macOS system Vision text recognition for chinese_audit.py (English pack, 2026-11-01).
// Reads a JSON list [{"id": "...", "path": "..."}] and writes
// {"engine": "vision", "results": [{"id", "ok", "error", "width", "height",
//   "items": [{"text", "confidence", "box": [x, y, w, h], "candidates": [{"text", "confidence"}]}]}]}
// Box is normalised (0..1, origin bottom-left, Vision's convention).
// Usage: ocr_vision <list.json> <out.json>     (or: swift ocr_vision.swift <list.json> <out.json>)
// Settings: accurate, languages zh-Hans + zh-Hant + en-US, no language correction.
import Foundation
import Vision
import ImageIO

struct Job: Decodable { let id: String; let path: String }

func recognize(_ job: Job) -> [String: Any] {
    var row: [String: Any] = ["id": job.id, "ok": false]
    let url = URL(fileURLWithPath: job.path)
    guard let source = CGImageSourceCreateWithURL(url as CFURL, nil),
          let image = CGImageSourceCreateImageAtIndex(source, 0, nil) else {
        row["error"] = "cannot read image"
        return row
    }
    row["width"] = image.width
    row["height"] = image.height
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = false
    request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]
    let handler = VNImageRequestHandler(cgImage: image, options: [:])
    do {
        try handler.perform([request])
    } catch {
        row["error"] = "vision failed: \(error)"
        return row
    }
    var items: [[String: Any]] = []
    for obs in request.results ?? [] {
        let cands = obs.topCandidates(3)
        guard let best = cands.first else { continue }
        let b = obs.boundingBox
        items.append([
            "text": best.string,
            "confidence": Double(best.confidence),
            "box": [Double(b.origin.x), Double(b.origin.y), Double(b.size.width), Double(b.size.height)],
            "candidates": cands.map { ["text": $0.string, "confidence": Double($0.confidence)] },
        ])
    }
    row["ok"] = true
    row["items"] = items
    return row
}

let args = CommandLine.arguments
if args.count < 3 {
    FileHandle.standardError.write("usage: ocr_vision <list.json> <out.json>\n".data(using: .utf8)!)
    exit(2)
}
do {
    let data = try Data(contentsOf: URL(fileURLWithPath: args[1]))
    let jobs = try JSONDecoder().decode([Job].self, from: data)
    var results: [[String: Any]] = []
    for job in jobs {
        autoreleasepool { results.append(recognize(job)) }
    }
    let doc: [String: Any] = ["engine": "vision", "results": results]
    let out = try JSONSerialization.data(withJSONObject: doc, options: [])
    try out.write(to: URL(fileURLWithPath: args[2]))
} catch {
    FileHandle.standardError.write("ocr_vision error: \(error)\n".data(using: .utf8)!)
    exit(1)
}
