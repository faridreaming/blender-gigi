# SPDX-License-Identifier: GPL-3.0-or-later
"""Jarak geodesik di mesh dari sebuah kurva (docs/PHASE2.md §5.3).

Vertex di sekitar kurva menjadi sumber dengan jarak awal = jarak eksak vertex itu ke kurva (bukan 0),
sehingga jarak tidak bergeser setengah sel. Dua metode:
- "fmm" (default): fast marching di segitiga (Kimmel dan Sethian 1998): setiap segitiga dengan dua vertex yang
  sudah diketahui memperbarui vertex ketiga dengan muka gelombang planar. Untuk jarak ke kurva (muka gelombang
  hampir planar) jauh lebih tepat daripada graf; segitiga yang arahnya tidak "dari dalam" segitiga memakai
  pembaruan edge.
- "graph": Dijkstra di graf edge. Selalu sama atau lebih panjang dari jarak sebenarnya (jalur mengikuti edge).
Galat keduanya diukur di tes dan benchmark (PHASE2.md §5.3).
"""

from __future__ import annotations

import heapq

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

from .geometry import MeshProjector, unique_edges
from .mesh_data import MeshData


def _distance_to_polyline(points: np.ndarray, polyline: np.ndarray) -> np.ndarray:
    from .synthetic import distance_to_polyline

    return distance_to_polyline(points, polyline, closed=True)


def _fast_marching(vertices: np.ndarray, faces: np.ndarray, allowed: np.ndarray, seed_idx: np.ndarray,
                   seed_dist: np.ndarray) -> np.ndarray:
    n = len(vertices)
    faces = faces[allowed[faces].all(axis=1)]
    order = np.argsort(faces.ravel(), kind="stable")
    owner = np.repeat(np.arange(len(faces)), 3)[order]
    starts = np.searchsorted(faces.ravel()[order], np.arange(n + 1))
    dist = np.full(n, np.inf)
    dist[seed_idx] = seed_dist
    known = np.zeros(n, dtype=bool)
    heap = [(float(d), int(i)) for i, d in zip(seed_idx, seed_dist)]
    heapq.heapify(heap)
    vx = vertices.tolist()
    flist = faces.tolist()

    def solve(c, a, b):
        ta, tb = dist[a], dist[b]
        pa, pb, pc = vx[a], vx[b], vx[c]
        ax, ay, az = pa[0] - pc[0], pa[1] - pc[1], pa[2] - pc[2]
        bx, by, bz = pb[0] - pc[0], pb[1] - pc[1], pb[2] - pc[2]
        aa = ax * ax + ay * ay + az * az
        bb = bx * bx + by * by + bz * bz
        ab = ax * bx + ay * by + az * bz
        edge = min(ta + aa ** 0.5, tb + bb ** 0.5)
        det = aa * bb - ab * ab
        if det <= 1e-18:
            return edge
        # Q = G^-1, G = [[aa, ab], [ab, bb]]
        q00, q01, q11 = bb / det, -ab / det, aa / det
        eqe = q00 + 2 * q01 + q11
        eqq = (q00 + q01) * ta + (q01 + q11) * tb
        qqq = q00 * ta * ta + 2 * q01 * ta * tb + q11 * tb * tb
        disc = eqq * eqq - eqe * (qqq - 1.0)
        if disc < 0:
            return edge
        tc = (eqq + disc ** 0.5) / eqe
        r0, r1 = ta - tc, tb - tc
        alpha = q00 * r0 + q01 * r1
        beta = q01 * r0 + q11 * r1
        if alpha <= 0 and beta <= 0 and tc >= max(ta, tb):
            return min(tc, edge)
        return edge

    while heap:
        d, v = heapq.heappop(heap)
        if known[v] or d > dist[v]:
            continue
        known[v] = True
        for fi in owner[starts[v]:starts[v + 1]]:
            tri = flist[fi]
            for c in tri:
                if known[c]:
                    continue
                others = [x for x in tri if x != c]
                a, b = others
                if known[a] and known[b]:
                    new = solve(c, a, b)
                else:
                    k = a if known[a] else b
                    pk, pc = vx[k], vx[c]
                    new = dist[k] + ((pk[0] - pc[0]) ** 2 + (pk[1] - pc[1]) ** 2 + (pk[2] - pc[2]) ** 2) ** 0.5
                if new < dist[c]:
                    dist[c] = new
                    heapq.heappush(heap, (new, c))
    return _relax(vertices, faces, dist, np.isin(np.arange(n), seed_idx))


def _relax(vertices: np.ndarray, faces: np.ndarray, dist: np.ndarray, fixed: np.ndarray,
           iterations: int = 20, tol: float = 1e-7) -> np.ndarray:
    """Putaran relaksasi tervektorisasi: setiap vertex dihitung ulang dari dua vertex lain di setiap segitiganya
    (muka gelombang planar bila arahnya dari dalam segitiga), lalu diambil minimumnya. Memperbaiki vertex yang
    di fast marching terlanjur ditetapkan lewat pembaruan edge (segitiga tumpul)."""
    dist = dist.copy()
    c_all, a_all, b_all = _ring_pairs(faces, len(vertices))
    # Hanya segitiga maya dengan sudut di c < 120 derajat: pasangan yang hampir berseberangan membuat taksiran
    # terlalu kecil karena tetangga di permukaan lengkung tidak sebidang dengan c.
    ua = vertices[a_all] - vertices[c_all]
    ub = vertices[b_all] - vertices[c_all]
    cosang = np.einsum("ij,ij->i", ua, ub) / np.maximum(np.linalg.norm(ua, axis=1) * np.linalg.norm(ub, axis=1), 1e-18)
    keep = cosang > np.cos(np.radians(120.0))
    c_all, a_all, b_all = c_all[keep], a_all[keep], b_all[keep]
    for _ in range(iterations):
        best = dist.copy()
        for c, a, b in ((c_all, a_all, b_all),):
            ta, tb = dist[a], dist[b]
            ok = np.isfinite(ta) & np.isfinite(tb)
            va, vb = vertices[a] - vertices[c], vertices[b] - vertices[c]
            aa = np.einsum("ij,ij->i", va, va)
            bb = np.einsum("ij,ij->i", vb, vb)
            ab = np.einsum("ij,ij->i", va, vb)
            edge = np.minimum(ta + np.sqrt(aa), tb + np.sqrt(bb))
            det = aa * bb - ab * ab
            with np.errstate(divide="ignore", invalid="ignore"):
                q00, q01, q11 = bb / det, -ab / det, aa / det
                eqe = q00 + 2 * q01 + q11
                eqq = (q00 + q01) * ta + (q01 + q11) * tb
                qqq = q00 * ta * ta + 2 * q01 * ta * tb + q11 * tb * tb
                disc = eqq * eqq - eqe * (qqq - 1.0)
                tc = (eqq + np.sqrt(np.maximum(disc, 0.0))) / eqe
                alpha = q00 * (ta - tc) + q01 * (tb - tc)
                beta = q01 * (ta - tc) + q11 * (tb - tc)
            planar = ok & (det > 1e-18) & (disc >= 0) & (alpha <= 0) & (beta <= 0) & (tc >= np.maximum(ta, tb))
            cand = np.where(planar, np.minimum(tc, edge), edge)
            cand[~ok] = np.inf
            np.minimum.at(best, c, cand)
        best[fixed] = dist[fixed]
        finite = np.isfinite(best) & np.isfinite(dist)
        change = float(np.max(np.abs(best[finite] - dist[finite]))) if finite.any() else 0.0
        dist = best
        if change < tol:
            break
    return dist


def _ring_pairs(faces: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Semua pasangan (a, b) tetangga cincin-1 untuk setiap vertex c: "segitiga maya" untuk pembaruan planar.
    Pasangan yang tidak berbagi segitiga dengan c menutup celah sudut tumpul."""
    edges = unique_edges(faces)
    nbr = np.concatenate([edges, edges[:, ::-1]])
    order = np.argsort(nbr[:, 0], kind="stable")
    nbr = nbr[order]
    starts = np.searchsorted(nbr[:, 0], np.arange(n + 1))
    cs, as_, bs = [], [], []
    for c in range(n):
        ring = nbr[starts[c]:starts[c + 1], 1]
        if len(ring) < 2:
            continue
        i, j = np.triu_indices(len(ring), 1)
        cs.append(np.full(len(i), c))
        as_.append(ring[i])
        bs.append(ring[j])
    if not cs:
        empty = np.zeros(0, dtype=int)
        return empty, empty, empty
    return np.concatenate(cs), np.concatenate(as_), np.concatenate(bs)


def distance_from_curve(mesh: MeshData, curve: np.ndarray, vertex_mask: np.ndarray | None = None,
                        seed_rings: int = 1, method: str = "fmm") -> np.ndarray:
    """Jarak geodesik (pendekatan) setiap vertex ke kurva tertutup di permukaan mesh, dalam mm.

    vertex_mask membatasi graf ke vertex tertentu (misalnya sisi preparasi), supaya jalur tidak lewat sisi lain
    margin. Vertex face yang dilewati kurva (ditambah seed_rings cincin) menjadi sumber. Vertex yang tidak
    terjangkau bernilai inf.
    """
    vertices = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces)
    curve = np.asarray(curve, float)
    n = len(vertices)
    allowed = np.ones(n, dtype=bool) if vertex_mask is None else np.asarray(vertex_mask, bool)

    edge_len = float(np.median(np.linalg.norm(vertices[faces[:, 0]] - vertices[faces[:, 1]], axis=1)))
    seg = np.linalg.norm(np.diff(np.vstack([curve, curve[:1]]), axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    dense_t = np.arange(0.0, s[-1], 0.25 * edge_len)
    closed = np.vstack([curve, curve[:1]])
    dense = np.stack([np.interp(dense_t, s, closed[:, k]) for k in range(3)], axis=1)
    _, crossed, _ = MeshProjector(mesh).closest(dense)
    seed = np.zeros(n, dtype=bool)
    seed[faces[np.unique(crossed)].ravel()] = True
    for _ in range(seed_rings):
        touch = seed[faces].any(axis=1)
        seed[faces[touch].ravel()] = True
    seed &= allowed
    if not seed.any():
        return np.full(n, np.inf)

    seed_idx = np.flatnonzero(seed)
    seed_dist = _distance_to_polyline(vertices[seed_idx], curve)
    if method == "fmm":
        return _fast_marching(vertices, faces, allowed, seed_idx, seed_dist)
    if method != "graph":
        raise ValueError(f"metode jarak tidak dikenal: {method!r}")
    edges = unique_edges(faces)
    keep = allowed[edges[:, 0]] & allowed[edges[:, 1]]
    edges = edges[keep]
    weights = np.linalg.norm(vertices[edges[:, 0]] - vertices[edges[:, 1]], axis=1)
    # Simpul maya n terhubung ke setiap sumber dengan bobot = jarak awal sumber itu.
    rows = np.concatenate([edges[:, 0], edges[:, 1], np.full(len(seed_idx), n)])
    cols = np.concatenate([edges[:, 1], edges[:, 0], seed_idx])
    data = np.concatenate([weights, weights, np.maximum(seed_dist, 1e-12)])
    graph = coo_matrix((data, (rows, cols)), shape=(n + 1, n + 1)).tocsr()
    dist = dijkstra(graph, directed=True, indices=n)[:n]
    dist[~allowed] = np.inf
    return dist
