const fs=require('node:fs/promises');
const path=require('node:path');
const table=Array.from({length:256},(_,i)=>{let c=i;for(let n=0;n<8;n++)c=c&1?0xedb88320^(c>>>1):c>>>1;return c>>>0;});
function crc32(data){let c=0xffffffff;for(const b of data)c=table[(c^b)&255]^(c>>>8);return(c^0xffffffff)>>>0;}
async function zipFolder(source,dest){
  const entries=[];
  async function walk(dir,prefix=''){for(const e of await fs.readdir(dir,{withFileTypes:true})){const rel=prefix+e.name;if(e.isDirectory())await walk(path.join(dir,e.name),rel+'/');else if(e.isFile())entries.push({name:rel,data:await fs.readFile(path.join(dir,e.name))});else throw Error('交接文件包含不支持的链接');}}
  await walk(source);const chunks=[],central=[];let offset=0;
  for(const e of entries){const name=Buffer.from(e.name),crc=crc32(e.data),local=Buffer.alloc(30);local.writeUInt32LE(0x04034b50,0);local.writeUInt16LE(20,4);local.writeUInt16LE(0x800,6);local.writeUInt32LE(crc,14);local.writeUInt32LE(e.data.length,18);local.writeUInt32LE(e.data.length,22);local.writeUInt16LE(name.length,26);chunks.push(local,name,e.data);
    const c=Buffer.alloc(46);c.writeUInt32LE(0x02014b50,0);c.writeUInt16LE(20,4);c.writeUInt16LE(20,6);c.writeUInt16LE(0x800,8);c.writeUInt32LE(crc,16);c.writeUInt32LE(e.data.length,20);c.writeUInt32LE(e.data.length,24);c.writeUInt16LE(name.length,28);c.writeUInt32LE(offset,42);central.push(c,name);offset+=local.length+name.length+e.data.length;
  }
  const directory=Buffer.concat(central),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50,0);end.writeUInt16LE(entries.length,8);end.writeUInt16LE(entries.length,10);end.writeUInt32LE(directory.length,12);end.writeUInt32LE(offset,16);await fs.writeFile(dest,Buffer.concat([...chunks,directory,end]));return dest;
}
module.exports={zipFolder,crc32};
