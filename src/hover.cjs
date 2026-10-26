function inside(point,bounds){return point.x>=bounds.x&&point.x<bounds.x+bounds.width&&point.y>=bounds.y&&point.y<bounds.y+bounds.height;}
// A manual close while the pointer remains on the tab requires a fresh entry.
function hoverTrigger(){let armed=true;return {
 closed(point,bounds){armed=!inside(point,bounds);},
 sample(point,bounds){if(!inside(point,bounds)){armed=true;return false;}if(!armed)return false;armed=false;return true;}
};}
module.exports={inside,hoverTrigger};
