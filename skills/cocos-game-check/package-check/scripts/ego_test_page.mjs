// Actual Ego Page transport only. Preserve requested viewport across Ego navigation,
// and capture real pixels without the mini-game host's synthetic devicePixelRatio.
import fs from 'node:fs/promises';
import path from 'node:path';
export function wrapEgoPage(page) {
  let metrics=null;
  async function apply(){
    if(!metrics)return;
    await page.cdp('Emulation.setDeviceMetricsOverride',metrics);
    await page.cdp('Emulation.setVisibleSize',{width:metrics.width,height:metrics.height});
  }
  return new Proxy(page,{get(target,key){
    if(key==='cdp')return async(method,params={},options)=>{
      if(method==='Emulation.setDeviceMetricsOverride')metrics={...params};
      const result=await target.cdp(method,params,options);
      if(method==='Emulation.setDeviceMetricsOverride')await target.cdp('Emulation.setVisibleSize',{width:params.width,height:params.height});
      return result;
    };
    if(key==='goto'||key==='reload')return async(...args)=>{const result=await target[key](...args);await apply();return result;};
    if(key==='screenshot')return async(options={})=>{
      if(!options.path||!path.isAbsolute(options.path))throw Error('Ego test screenshots need an absolute output path');
      await apply();
      const args={format:'png',captureBeyondViewport:!!options.fullPage};
      if(options.clip)args.clip={...options.clip,scale:1};
      const image=await target.cdp('Page.captureScreenshot',args);
      await fs.mkdir(path.dirname(options.path),{recursive:true});
      await fs.writeFile(options.path,Buffer.from(image.data,'base64'));
      return options.path;
    };
    const value=Reflect.get(target,key,target);return typeof value==='function'?value.bind(target):value;
  }});
}
