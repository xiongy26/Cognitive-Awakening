#!/usr/bin/env python3
"""口播稿自检工具：核对字数、每拍句数与句长、时长复核。
用法: python3 tools/check_script.py 口播文案/2-1_*.md
"""
import re, sys, glob

PUNCT = r'[，。！？、；：""''…—]'

def parse(path):
    s = open(path, encoding='utf-8').read()
    m = re.search(r'## 正文口播稿.*?\n(.*?)\n## 配套画面', s, re.S)
    if not m:
        return None
    beats = []
    cur = None
    for ln in m.group(1).split('\n'):
        ln = ln.strip()
        if not ln.startswith('>'):
            continue
        ln = ln.lstrip('>').strip().replace('**', '')
        if not ln:
            continue
        hm = re.match(r'^（\s*(\d+)\s*[-–]\s*(\d+)\s*秒', ln)
        if hm:
            cur = {'start': int(hm.group(1)), 'end': int(hm.group(2)), 'lines': []}
            beats.append(cur)
            continue
        if cur is not None:
            cur['lines'].append(ln.replace('**', ''))
    return s, beats

def report(path):
    s, beats = parse(path)
    if beats is None:
        print(f"{path}: 未找到正文口播稿"); return False
    ok = True
    all_lines = []
    print(f"\n=== {path} ===")
    for b in beats:
        text = ''.join(b['lines'])
        all_lines.extend(b['lines'])
        han = len(re.findall(r'[\u4e00-\u9fff]', text))
        pun = len(re.findall(PUNCT, text))
        sents = [x for x in re.split(r'(?<=[，。！？…—])', text) if x.strip()]
        longs = [x for x in sents if len(re.findall(r'[\u4e00-\u9fff]', x)) > 25]
        flag = ''
        if len(b['lines']) < 1 or len(b['lines']) > 8: flag += f' [句数{len(b["lines"])}]'
        if longs: flag += f' [超长句{len(longs)}]'
        print(f"  镜{b['start']}-{b['end']}秒 ({b['end']-b['start']:>2}秒) 句数{len(b['lines'])} 字数{han+pun}{flag}")
        for lg in longs:
            print(f"      超长: {lg.strip()}")
    body = ''.join(all_lines)
    han = len(re.findall(r'[\u4e00-\u9fff]', body))
    pun = len(re.findall(PUNCT, body))
    total = han + pun
    decl = re.search(r'## 正文口播稿[^\n]*?约\s*(\d+)\s*字', s)
    decl_n = int(decl.group(1)) if decl else -1
    sec = round(total / 260 * 60)
    print(f"  合计: 汉字{han} + 标点{pun} = {total}  | 标注约{decl_n}字 | ~{sec}秒")
    if not (240 <= total <= 260):
        print(f"  X 字数不在 240-260 区间 (当前 {total})"); ok = False
    if decl_n != total:
        print(f"  X 标注字数({decl_n})与实际({total})不一致"); ok = False
    tr = re.search(r'\*\*时长复核\*\*：(.+)', s)
    if tr:
        nums = [(int(a), int(b)) for a, b in re.findall(r'\((\d+)-(\d+)\)', tr.group(1))]
        # 拍段时间应首尾相接：0 -> 60，且不倒挂
        chain_ok = nums[0][0] == 0 and nums[-1][1] == 60
        for (s1, e1), (s2, e2) in zip(nums, nums[1:]):
            if s2 < e1:  # 允许 1 秒以内的衔接缝
                chain_ok = False
        spans = [e - s for s, e in nums]
        print(f"  时长复核: {' + '.join(map(str, spans))} = {sum(spans)}秒 (区间 {nums[0][0]}-{nums[-1][1]})")
        if not chain_ok:
            print(f"  X 拍段时间未首尾相接覆盖 0-60 秒"); ok = False
        if len(nums) != len(beats):
            print(f"  X 镜头数({len(nums)})与口播拍数({len(beats)})不符"); ok = False
    else:
        print("  X 缺少时长复核"); ok = False
    if len(beats) != 6:
        print(f"  X 口播拍数为 {len(beats)}，应为 6"); ok = False
    print(f"  {'通过' if ok else '未通过'}")
    return ok

if __name__ == '__main__':
    files = []
    for a in sys.argv[1:]:
        files.extend(sorted(glob.glob(a)) if '*' in a else [a])
    results = [report(f) for f in files]
    sys.exit(0 if all(results) else 1)
