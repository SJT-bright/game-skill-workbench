const {identity}=require('../ui/thread-selection.js');
const WORKFLOWS=['英化','重塑'];
function setGamePreferences(games,id,value,{roots=[]}={}){
 const game=games.find(g=>g.id===id);if(!game)throw Error('游戏不存在');
 if(value.workflow!==undefined&&!WORKFLOWS.includes(value.workflow))throw Error('请选择英化或重塑');
 if(value.pinned!==undefined&&typeof value.pinned!=='boolean')throw Error('置顶状态无效');
 const key=identity(game,roots).key;
 for(const g of games)if(identity(g,roots).key===key){if(value.workflow!==undefined)g.workflow=value.workflow;if(value.pinned!==undefined)g.pinned=value.pinned;}
 return game;
}
function inheritGamePreferences(game,games,{roots=[]}={}){const key=identity(game,roots).key,sibling=games.find(g=>g!==game&&identity(g,roots).key===key&&(g.workflow||g.pinned));if(sibling){game.workflow??=sibling.workflow;game.pinned??=sibling.pinned;}return game;}
module.exports={WORKFLOWS,setGamePreferences,inheritGamePreferences};
