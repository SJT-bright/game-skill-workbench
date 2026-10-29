const {contextBridge,ipcRenderer,webUtils}=require('electron');
contextBridge.exposeInMainWorld('dock',{
  call:async(method,value)=>{const r=await ipcRenderer.invoke('dock:call',method,value);if(!r.ok)throw Error(r.error);return r.value;},
  onState:callback=>{const fn=(_,s)=>callback(s);ipcRenderer.on('dock:state',fn);return()=>ipcRenderer.removeListener('dock:state',fn);},
  filePath:file=>webUtils.getPathForFile(file),
  drag:archive=>ipcRenderer.send('dock:drag',archive)
});
