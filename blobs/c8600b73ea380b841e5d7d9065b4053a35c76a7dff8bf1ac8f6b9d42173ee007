"""Validate business observations, not just an active Loading scene.
This is an evidence validator; it does not execute a game or establish truth of observations.
"""
import math

def validate_business(data):
    errors=[]
    def need(ok,message):
        if not ok:errors.append('STARTUP-BUSINESS: '+message)
    def moment(value):return type(value) in (int,float) and math.isfinite(value) and value>=0
    business=data.get('business',{})
    need(isinstance(business,dict),'business observations required')
    if not isinstance(business,dict):return errors
    home=business.get('home',{});play=business.get('play',{})
    if not isinstance(home,dict) or not isinstance(play,dict):return ['STARTUP-BUSINESS: home/play observations must be objects']
    need(home.get('visible') is True and home.get('required_assets_ready') is True,'visible HOME with required assets required')
    need(home.get('loading_overlay_gone') is True and home.get('play_interactable') is True,'Loading must be gone and PLAY usable')
    need(bool(home.get('node_path')),'HOME node identity required')
    need(home.get('lifecycle_complete') is True and home.get('after_draw_observed') is True,'HOME lifecycle and actual post-draw observation required')
    touch=play.get('touch',{})
    if not isinstance(touch,dict):touch={}
    need(touch.get('transport')=='ego_page_cdp' and moment(touch.get('at_ms')),'actual touch identity required')
    need(play.get('level_ready') is True and bool(play.get('level_identity')),'actual playable level identity required')
    need(isinstance(play.get('before'),dict) and bool(play.get('before')) and isinstance(play.get('after'),dict) and bool(play.get('after')) and play.get('before')!=play.get('after'),'observable gameplay change after touch required')
    need(moment(home.get('at_ms')) and moment(play.get('effect_at_ms')) and moment(touch.get('at_ms')) and home['at_ms']<=touch['at_ms']<play['effect_at_ms'],'HOME → touch → gameplay effect order required')
    need(not data.get('first_exception'),'first startup exception must not be hidden')
    return errors
