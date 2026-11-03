"""Shared stable tracks and independently compact camera display numbers."""
import math
from dataclasses import dataclass


def finite_point(value):
    return (isinstance(value, (list, tuple)) and len(value) == 2
            and all(isinstance(v, (int, float)) and math.isfinite(v) for v in value))


def observed_ids(views, judged_only=False):
    return {p.get('track_id') or p.get('person_id') for v in views.values()
            if v.get('valid') and v.get('assessment') for p in v['assessment']['persons']
            if (p.get('track_id') or p.get('person_id'))
            and (not judged_only or p.get('state') in {'SAFE','DANGER'})}


def bbox_iou(a, b):
    if (not isinstance(a,(list,tuple)) or not isinstance(b,(list,tuple))
            or len(a)!=4 or len(b)!=4 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in [*a,*b])):
        return 0.
    overlap = max(0.,min(a[2],b[2])-max(a[0],b[0]))*max(0.,min(a[3],b[3])-max(a[1],b[1]))
    union = max(0.,a[2]-a[0])*max(0.,a[3]-a[1])+max(0.,b[2]-b[0])*max(0.,b[3]-b[1])-overlap
    return overlap/union if union>0 else 0.


def nearest_assignment(candidates):
    """Maximum-cardinality, minimum-cost matching; each detection and ID once.

    Hungarian assignment with dummy columns for unmatched detections. Pure Python
    keeps tracking independent of the host's incompatible SciPy/NumPy versions.
    """
    if not candidates:
        return {}
    rows = sorted({i for _, i, _ in candidates})
    tracks = sorted({pid for _, _, pid in candidates}, key=lambda pid: int(pid.removeprefix('person')))
    n, count = len(rows), len(tracks)
    dummy = (max(cost for cost, _, _ in candidates)+1)*(n+1)
    matrix = [[dummy*(n+1)]*count + [dummy]*n for _ in rows]
    row_index, columns = {i:k for k,i in enumerate(rows)}, {pid:k for k,pid in enumerate(tracks)}
    for cost, i, pid in candidates:
        r, c = row_index[i], columns[pid]
        matrix[r][c] = min(matrix[r][c], cost)
    m = count+n
    u, v, owner, way = [0.]*(n+1), [0.]*(m+1), [0]*(m+1), [0]*(m+1)
    for i in range(1,n+1):
        owner[0], column = i, 0
        minimum, used = [math.inf]*(m+1), [False]*(m+1)
        while True:
            used[column] = True
            source, delta, following = owner[column], math.inf, 0
            for j in range(1,m+1):
                if not used[j]:
                    cost = matrix[source-1][j-1]-u[source]-v[j]
                    if cost < minimum[j]:
                        minimum[j], way[j] = cost, column
                    if minimum[j] < delta:
                        delta, following = minimum[j], j
            for j in range(m+1):
                if used[j]:
                    u[owner[j]] += delta
                    v[j] -= delta
                else:
                    minimum[j] -= delta
            column = following
            if not owner[column]:
                break
        while column:
            previous = way[column]
            owner[column] = owner[previous]
            column = previous
    return {rows[owner[j]-1]: tracks[j-1] for j in range(1,count+1)
            if owner[j] and matrix[owner[j]-1][j-1] < dummy}


@dataclass(init=False)
class PersonTracker:
    max_distance_m: float
    ttl_ns: int
    fallback_distance_px: float
    next_id: int
    tracks: dict
    last_seq: dict
    appearance_order: list
    seen_cameras: dict
    camera_order: dict

    def __init__(self, max_distance_m=.15, ttl_seconds=2., fallback_distance_px=80.):
        self.max_distance_m = max_distance_m
        self.ttl_ns = int(ttl_seconds*1e9)
        self.fallback_distance_px = fallback_distance_px
        self.next_id = 1
        self.tracks, self.last_seq = {}, {}
        self.appearance_order, self.seen_cameras = [], {}
        self.camera_order = {}

    def active_ids(self, now_ns):
        return [pid for pid,t in self.tracks.items() if now_ns-t['last_seen_ns'] <= self.ttl_ns]

    def label_map(self, now_ns, visible_ids=None, judged_ids=None, camera_id=None):
        active = sorted(self.active_ids(now_ns), key=lambda pid:int(pid.removeprefix('person')))
        if camera_id is not None:
            own = {pid for pid in active if camera_id in self.tracks[pid]['cameras']}
            active = [pid for pid in self.camera_order.get(camera_id,[]) if pid in own]
            active += sorted(own-set(active),key=lambda pid:int(pid.removeprefix('person')))
        if visible_ids is None:
            visible_ids = {pid for pid in active for cid,p in self.tracks[pid]['cameras'].items()
                           if (camera_id is None or cid == camera_id)
                           and p['frame_seq'] == self.last_seq.get(cid)
                           and now_ns-p['capture_ns'] <= self.ttl_ns}
        if judged_ids is None:
            judged_ids = {pid for pid in active if pid in visible_ids
                          for cid,p in self.tracks[pid]['cameras'].items()
                          if (camera_id is None or cid == camera_id)
                          and p['frame_seq'] == self.last_seq.get(cid)
                          and now_ns-p['capture_ns'] <= self.ttl_ns
                          and p.get('state') in {'SAFE','DANGER'}}
        # Missing tracks remain recoverable but do not reserve the first numbers.
        if camera_id is not None:
            # UNKNOWN is still a visible person in this camera. Risk state must
            # not reorder that camera's remembered arrival sequence.
            ordered = ([pid for pid in active if pid in visible_ids] +
                       [pid for pid in active if pid not in visible_ids])
        else:
            ordered = ([pid for pid in active if pid in judged_ids] +
                       [pid for pid in active if pid in visible_ids and pid not in judged_ids] +
                       [pid for pid in active if pid not in visible_ids and pid not in judged_ids])
        return {pid:f'person{i}' for i,pid in enumerate(ordered,start=1)}

    @staticmethod
    def apply_labels(rows, labels):
        for row in rows:
            tid = row.get('track_id') or row.get('person_id')
            if tid:
                row.update(track_id=tid,person_id=labels.get(tid))

    def prune(self, now_ns):
        active = set(self.active_ids(now_ns))
        self.tracks = {pid:t for pid,t in self.tracks.items() if pid in active}
        self.appearance_order = [pid for pid in self.appearance_order if pid in active]
        self.seen_cameras = {pid:cids for pid,cids in self.seen_cameras.items() if pid in active}
        self.camera_order = {cid:[pid for pid in order if pid in active]
                             for cid,order in self.camera_order.items()}

    def invalidate_camera(self, cid):
        for track in self.tracks.values():
            track['cameras'].pop(cid,None)

    @staticmethod
    def predicted(previous, key, stamp, limit):
        point = previous.get(key)
        if not finite_point(point):
            return None
        velocity = previous.get('velocity_'+key)
        if not finite_point(velocity):
            return point
        seconds = min(.3,max(0.,(stamp-previous['capture_ns'])/1e9))
        shift = [v*seconds for v in velocity]
        length = math.hypot(*shift)
        scale = min(1.,limit/length) if length else 1.
        return [point[i]+shift[i]*scale for i in (0,1)]

    def update(self, ground, assessment):
        cid,seq,stamp = (ground[k] for k in ('camera_id','frame_seq','capture_ns'))
        if seq <= self.last_seq.get(cid,-1):
            return
        self.last_seq[cid] = seq
        self.prune(stamp)
        revision,rows = ground['calibration']['revision'],assessment['persons']
        source = {p['observation_id']:p for p in ground['persons']}
        source_rows = [source[row['observation_id']] for row in rows]
        points = [p.get('xy') if ground['valid'] and p.get('eligible',True)
                  and finite_point(p.get('xy')) else None for p in source_rows]
        # A clipped foot just beyond the calibrated board can still help
        # establish cross-camera identity, though it is not a reliable local
        # motion measurement.
        cross_points = [p.get('xy') if ground['valid'] and finite_point(p.get('xy'))
                        and set(p.get('reasons',[])) <= {'OUTSIDE_CALIBRATED_GROUND', 'CLIPPED_BBOX'}
                        else None for p in source_rows]
        assigned,methods,used = {},{},set()

        def assign(candidates, method):
            edges = [(cost,i,pid) for cost,i,pid in candidates if i not in assigned and pid not in used]
            for i,pid in nearest_assignment(edges).items():
                assigned[i],methods[i] = pid,method
                used.add(pid)

        own_ground,own_pixels = [],[]
        for i,point in enumerate(points):
            for pid,track in self.tracks.items():
                previous = track['cameras'].get(cid)
                # Each binding owns separate camera coordinates. The other
                # camera may keep this identity alive through a long occlusion.
                if previous and previous['revision'] == revision:
                    if point is not None and finite_point(previous['xy']):
                        predicted = self.predicted(previous,'xy',stamp,self.max_distance_m)
                        distance = math.dist(point,predicted)
                        if distance <= self.max_distance_m:
                            own_ground.append((distance/self.max_distance_m,i,pid))
                        elif (finite_point(rows[i].get('anchor')) and finite_point(previous.get('anchor'))
                              and bbox_iou(rows[i].get('bbox'),previous.get('bbox')) >= .5):
                            pixels = math.dist(rows[i]['anchor'],previous['anchor'])
                            if pixels <= self.fallback_distance_px:
                                own_pixels.append((1.+pixels/self.fallback_distance_px,i,pid))
                    elif finite_point(rows[i].get('anchor')) and finite_point(previous.get('anchor')):
                        predicted = self.predicted(previous,'anchor',stamp,self.fallback_distance_px)
                        distance = math.dist(rows[i]['anchor'],predicted)
                        if distance <= self.fallback_distance_px:
                            own_pixels.append((distance/self.fallback_distance_px,i,pid))
                        else:
                            # Detector truncation can corrupt a velocity estimate;
                            # a return near the last measured position is recoverable.
                            measured = math.dist(rows[i]['anchor'],previous['anchor'])
                            if measured <= self.fallback_distance_px:
                                own_pixels.append((1.+measured/self.fallback_distance_px,i,pid))
        ground_edges = {(i,pid) for _,i,pid in own_ground}
        assign(own_ground+[(cost+.25,i,pid) for cost,i,pid in own_pixels],'own_camera')
        for i,pid in assigned.items():
            methods[i] = 'homography_nearest' if (i,pid) in ground_edges else 'camera_pixels_only'
        # Establish a binding once, in appearance order, then follow that
        # camera's own motion. Never compare two views to overwrite an existing
        # binding: homography errors and perspective can give different XYs.
        # Disappeared one-frame detections cannot take the next camera's arrival.
        eligible = [pid for pid in self.appearance_order if pid not in used
                    and cid not in self.seen_cameras[pid]
                    and any(key != cid and abs(stamp-p['capture_ns']) <= self.ttl_ns
                            for key,p in self.tracks[pid]['cameras'].items())]
        visible = [pid for pid in eligible
                   if any(key != cid and p['frame_seq'] == self.last_seq.get(key)
                          and abs(stamp-p['capture_ns']) <= self.ttl_ns
                          for key,p in self.tracks[pid]['cameras'].items())]
        # Prefer the current roster over vanished temporary detections. If the
        # other view missed this frame entirely, retain short-occlusion pairing.
        pending = visible or sorted(eligible,key=lambda pid:
            (-max(p['capture_ns'] for key,p in self.tracks[pid]['cameras'].items() if key != cid),
             int(pid.removeprefix('person'))))
        arrivals = [i for i in range(len(rows)) if i not in assigned]
        # The cameras can detect the same people in opposite orders, even when
        # only one new detection arrives in this frame. Allow twice the local
        # motion gate for cross-view calibration error, then fall back to the
        # arrival order only when no projected candidate is close enough.
        cross_distance_m = self.max_distance_m * 2
        if arrivals and pending:
            cross = []
            for i in arrivals:
                if cross_points[i] is None:
                    continue
                for pid in pending:
                    others = [p for key,p in self.tracks[pid]['cameras'].items() if key != cid
                              and p['frame_seq'] == self.last_seq.get(key)
                              and finite_point(p.get('cross_xy'))
                              and abs(stamp-p['capture_ns']) <= self.ttl_ns]
                    if others:
                        other = max(others,key=lambda p:p['capture_ns'])
                        predicted = self.predicted(other,'cross_xy',stamp,cross_distance_m)
                        distance = math.dist(cross_points[i],predicted)
                        if distance <= cross_distance_m:
                            cross.append((distance/cross_distance_m,i,pid))
            assign(cross,'cross_camera_homography')
        for i in arrivals:
            if i in assigned:
                continue
            candidate = next((pid for pid in pending if pid not in used),None)
            if candidate:
                assigned[i],methods[i] = candidate,'shared_appearance_order'
                used.add(candidate)
        for i,row in enumerate(rows):
            pid = assigned.get(i)
            if pid is None:
                pid = f'person{self.next_id}'
                self.next_id += 1
                self.appearance_order.append(pid)
                self.seen_cameras[pid] = set()
            self.seen_cameras[pid].add(cid)
            track = self.tracks.setdefault(pid,{'last_seen_ns':stamp,'cameras':{}})
            previous = track['cameras'].get(cid)
            current = {'xy':points[i],'cross_xy':cross_points[i],
                       'anchor':row.get('anchor'),'bbox':row.get('bbox'),'revision':revision,
                       'state':row.get('state'),
                       'capture_ns':stamp,'frame_seq':seq}
            if previous and previous['revision'] == revision:
                seconds = (stamp-previous['capture_ns'])/1e9
                if 0 < seconds <= self.ttl_ns/1e9:
                    for key in ('xy','anchor'):
                        if key == 'xy' and methods.get(i) == 'camera_pixels_only':
                            continue
                        if finite_point(current[key]) and finite_point(previous.get(key)):
                            velocity = [(current[key][j]-previous[key][j])/seconds for j in (0,1)]
                            old = previous.get('velocity_'+key)
                            current['velocity_'+key] = [(v+old[j])/2 for j,v in enumerate(velocity)] if finite_point(old) else velocity
            track['last_seen_ns'] = max(stamp,track['last_seen_ns'])
            track['cameras'][cid] = current
            row.update(track_id=pid,person_id=pid,tracking_method=methods.get(i,'new_track'))
            source[row['observation_id']].update(track_id=pid,person_id=pid)
        order = self.camera_order.setdefault(cid,[])
        # Detections in a single first-seen frame have no temporal order.
        # Keep their shared identity order; append later arrivals independently.
        newcomers = {row['track_id'] for row in rows}-set(order)
        order.extend(sorted(newcomers,key=lambda pid:int(pid.removeprefix('person'))))
        labels = self.label_map(stamp,camera_id=cid)
        self.apply_labels(rows,labels)
        self.apply_labels(ground['persons'],labels)
