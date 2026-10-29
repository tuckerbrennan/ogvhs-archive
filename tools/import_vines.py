#!/usr/bin/env python3
"""Merge a local video folder and/or CSV/JSON metadata into data/vines.json.

Never uploads video files and never deletes catalog entries. Only verified short Vine IDs
(11 alphanumeric characters) are used as record keys. AppleDouble files are ignored.
"""
import argparse
import csv
import datetime as dt
import json
import re
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT=Path(__file__).resolve().parent.parent
ID=re.compile(r'^[A-Za-z0-9]{11}$')
VIDEO_NAME=re.compile(r'(?<![A-Za-z0-9])([A-Za-z0-9]{11})(?![A-Za-z0-9])')
VIDEO_EXT={'.mp4','.m4v','.mov','.webm'}


def infer_id(filename):
    name=Path(filename).name
    if name.startswith('._') or name.startswith('.') or Path(name).suffix.casefold() not in VIDEO_EXT:
        return None
    stem=Path(name).stem
    if stem.endswith('.sub'): stem=stem[:-4]
    if ID.fullmatch(stem): return stem
    hits=VIDEO_NAME.findall(stem)
    return hits[0] if len(hits)==1 else None


def first(row, *names):
    lower={str(k).lower().replace('_','').replace(' ',''):v for k,v in row.items()}
    for name in names:
        val=lower.get(name.lower().replace('_','').replace(' ',''))
        if val is not None and str(val).strip()!='':
            return val
    return None


def read_metadata(path):
    if not path:return []
    ext=path.suffix.lower()
    if ext=='.json':
        raw=json.loads(path.read_text(encoding='utf-8-sig'))
        if isinstance(raw,list):return raw
        if isinstance(raw,dict):
            for key in ('posts','videos','vines','data','records'):
                if isinstance(raw.get(key),list):return raw[key]
        raise ValueError('JSON must be an array of posts or an object with a posts/videos/vines/data/records array')
    if ext=='.csv':
        with path.open(encoding='utf-8-sig',newline='') as f:
            return list(csv.DictReader(f))
    raise ValueError('Metadata input must be .csv or .json')


def normalize_date(value):
    if value is None:return None
    if isinstance(value,(int,float)) or (isinstance(value,str) and value.strip().isdigit()):
        number=float(value)
        if number>1e11: number/=1000
        return dt.datetime.fromtimestamp(number,dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        date=dt.datetime.fromisoformat(str(value).strip().replace('Z','+00:00'))
        return date.date().isoformat() if len(str(value).strip())==10 else date.isoformat()
    except ValueError:
        raise ValueError(f'Unsupported date: {value!r}')


def http_url(v):
    if not v:return None
    text=str(v).strip()
    p=urlparse(text)
    return text if p.scheme in ('http','https') and p.netloc else None


def merge(existing, files, metadata, media_base=None):
    records={r['vineId']:dict(r) for r in existing}
    inserted=updated=ignored=0
    notes=[]
    now=dt.date.today().isoformat()
    for file in files:
        name=file.name
        vid=infer_id(name)
        if not vid:
            ignored+=1
            continue
        current=records.setdefault(vid, {'vineId':vid,'rawCaption':None,'publishedAt':None,'tags':[]})
        if not current.get('sourceFilename'):
            current['sourceFilename']=name
            updated+=1
        if not current.get('restoredAt'):
            current['restoredAt']=now
        if media_base and not current.get('videoUrl'):
            base=media_base.rstrip('/')
            # The video must already have been uploaded to this HTTP(S) location.
            current['videoUrl']=f'{base}/{quote(name)}'
    for row in metadata:
        if not isinstance(row,dict):
            notes.append('Skipped metadata item that was not an object')
            continue
        vid=first(row,'vineId','vine_id','postId','post_id','id','videoId')
        vid=str(vid).strip() if vid else None
        if not vid or not ID.fullmatch(vid):
            notes.append(f'Skipped metadata row without a valid 11-character Vine ID: {str(vid)[:30]}')
            continue
        if vid not in records:
            records[vid]={'vineId':vid,'rawCaption':None,'publishedAt':None,'tags':[],'restoredAt':now}
            inserted+=1
        record=records[vid]
        caption=first(row,'rawCaption','caption','description','text','title')
        if caption is not None and not record.get('rawCaption'):
            record['rawCaption']=str(caption)
            updated+=1
        when=first(row,'publishedAt','published_at','createdAt','created_at','postDate','date','timestamp')
        if when is not None and not record.get('publishedAt'):
            try:
                record['publishedAt']=normalize_date(when)
                updated+=1
            except (ValueError,OverflowError,OSError) as err:
                notes.append(f'{vid}: {err}')
        tags=first(row,'tags','hashtags')
        if tags and not record.get('tags'):
            if isinstance(tags,list):record['tags']=[str(t).lstrip('#') for t in tags]
            elif isinstance(tags,str):record['tags']=[t.strip().lstrip('#') for t in tags.split(',') if t.strip()]
        link=first(row,'videoUrl','video_url','url')
        if link and not record.get('videoUrl'):
            valid=http_url(link)
            if valid:record['videoUrl']=valid
        thumbnail=first(row,'thumbnailUrl','thumbnail_url','poster')
        if thumbnail and not record.get('thumbnailUrl'):
            valid=http_url(thumbnail)
            if valid:record['thumbnailUrl']=valid
    return sorted(records.values(),key=lambda r:r['vineId']),{'media_files_skipped':ignored,'metadata_new_rows':inserted,'fields_added':updated,'notes':notes}


def main():
    cli=argparse.ArgumentParser(description='Merge original Vine MP4 filenames and/or CSV/JSON metadata into the OG VHS archive.')
    cli.add_argument('--folder',type=Path,help='Directory with original videos, recursively searched')
    cli.add_argument('--metadata',type=Path,help='CSV or JSON metadata export, if recovered')
    cli.add_argument('--media-base-url',help='Public URL where the video files have already been uploaded; optional')
    cli.add_argument('--dry-run',action='store_true',help='Print counts without changing the catalog')
    cli.add_argument('--catalog',type=Path,default=ROOT/'data'/'vines.json')
    args=cli.parse_args()
    if not args.folder and not args.metadata:cli.error('Specify --folder and/or --metadata')
    if args.folder and not args.folder.is_dir():cli.error(f'Not a directory: {args.folder}')
    if args.metadata and not args.metadata.is_file():cli.error(f'Not a file: {args.metadata}')
    if args.media_base_url and not http_url(args.media_base_url):cli.error('--media-base-url must be an HTTP(S) URL')
    original=json.loads(args.catalog.read_text()) if args.catalog.is_file() else []
    videos=sorted((f for f in args.folder.rglob('*') if f.is_file()),key=str) if args.folder else []
    rows=read_metadata(args.metadata)
    records,report=merge(original,videos,rows,args.media_base_url)
    print(f'Catalog: {len(original)} → {len(records)} records')
    for k,v in report.items():print(k+':',v if k!='notes' else '; '.join(v[:20]))
    if args.dry_run: print('Dry run: no files changed');return
    args.catalog.parent.mkdir(parents=True,exist_ok=True)
    args.catalog.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved',args.catalog)

if __name__=='__main__':main()
