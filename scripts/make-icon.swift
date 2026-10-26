import AppKit
let root=CommandLine.arguments[1]
let image=NSImage(size:NSSize(width:512,height:512))
image.lockFocus()
NSColor(calibratedRed:0.90,green:0.94,blue:0.86,alpha:1).setFill()
NSBezierPath(roundedRect:NSRect(x:8,y:8,width:496,height:496),xRadius:112,yRadius:112).fill()
NSColor(calibratedRed:0.19,green:0.40,blue:0.33,alpha:1).setFill()
let p=NSBezierPath();p.move(to:NSPoint(x:160,y:330));p.line(to:NSPoint(x:352,y:330));p.curve(to:NSPoint(x:420,y:174),controlPoint1:NSPoint(x:398,y:330),controlPoint2:NSPoint(x:430,y:220));p.curve(to:NSPoint(x:364,y:157),controlPoint1:NSPoint(x:416,y:140),controlPoint2:NSPoint(x:391,y:135));p.line(to:NSPoint(x:314,y:200));p.line(to:NSPoint(x:198,y:200));p.line(to:NSPoint(x:148,y:157));p.curve(to:NSPoint(x:92,y:174),controlPoint1:NSPoint(x:120,y:135),controlPoint2:NSPoint(x:96,y:140));p.curve(to:NSPoint(x:160,y:330),controlPoint1:NSPoint(x:82,y:220),controlPoint2:NSPoint(x:114,y:330));p.close();p.fill()
NSColor(calibratedRed:0.91,green:0.95,blue:0.87,alpha:1).setFill()
NSBezierPath(roundedRect:NSRect(x:144,y:246,width:72,height:20),xRadius:5,yRadius:5).fill();NSBezierPath(roundedRect:NSRect(x:170,y:220,width:20,height:72),xRadius:5,yRadius:5).fill()
NSColor(calibratedRed:0.75,green:0.83,blue:0.58,alpha:1).setFill();NSBezierPath(ovalIn:NSRect(x:315,y:267,width:23,height:23)).fill();NSBezierPath(ovalIn:NSRect(x:351,y:230,width:23,height:23)).fill()
NSColor(calibratedRed:0.46,green:0.63,blue:0.43,alpha:1).setFill();NSBezierPath(ovalIn:NSRect(x:348,y:367,width:24,height:24)).fill();NSBezierPath(ovalIn:NSRect(x:384,y:390,width:12,height:12)).fill()
image.unlockFocus()
let png=NSBitmapImageRep(data:image.tiffRepresentation!)!.representation(using:.png,properties:[:])!
try png.write(to:URL(fileURLWithPath:root+"/ui/window-icon.png"))
let iconset=root+"/.qa/GameDeskSkill.iconset";try FileManager.default.createDirectory(atPath:iconset,withIntermediateDirectories:true)
for size in [16,32,128,256,512] { for scale in [1,2] {let px=size*scale;let rep=NSBitmapImageRep(bitmapDataPlanes:nil,pixelsWide:px,pixelsHigh:px,bitsPerSample:8,samplesPerPixel:4,hasAlpha:true,isPlanar:false,colorSpaceName:.deviceRGB,bytesPerRow:0,bitsPerPixel:0)!;NSGraphicsContext.saveGraphicsState();NSGraphicsContext.current=NSGraphicsContext(bitmapImageRep:rep);image.draw(in:NSRect(x:0,y:0,width:px,height:px));NSGraphicsContext.restoreGraphicsState();let file=iconset+"/icon_\(size)x\(size)"+(scale==2 ? "@2x" : "")+".png";try rep.representation(using:.png,properties:[:])!.write(to:URL(fileURLWithPath:file))}}
