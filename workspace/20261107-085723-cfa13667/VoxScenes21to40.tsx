import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {GeoJson3DMapStage, VoxBeatSceneProps} from '../china-crime-newsroom';
import {
  CHENGRUILONG_GEO_ROUTES,
  CHENGRUILONG_LANDMARKS,
  CHENGRUILONG_PLATES,
  loupeAsset,
  plateAsset,
  propAsset,
} from './voxGeoData';
import {
  p12,
  camAt,
  Desk,
  World,
  CutoutPopOutStage,
  TornPaperSplitReveal,
  PaperUnfoldCollage,
  ScrapbookCollageAssembly,
  LoupePhotoCutout,
} from '../vox-editorial-desk';

// VOX_21 (B065-V01): "도주 기간 동안 그는 다섯 개의 가짜 이름을 번갈아 쓰며 철저히 다른 사람으로 위장해 살았습니다."
export const VoxScene21: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb FIVE_ALIAS_IDENTITY_SHIFT
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);
  const mainPlate = plateAsset('plate_21.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <TornPaperSplitReveal
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          coverPhotoSrc={mainPlate}
          coverTitle="5개 가명 순환 위장"
          coverTag="5개 가명 위장"
          revealPhotoSrc={mainPlate}
          revealTitle="최종 가명 저우전칭 고착"
          revealTag="ZHOU QUANQING"
          cutoutSrc={propAsset('prop_11_five_alias_slips.png')}
          cutoutCaption="5종 위조 임시 신분증"
          cutoutBadge="가명 교체"
          clippingHeadline="13년간 5개 가명 순환 위장 기록"
          clippingBody="성(省) 이동 시마다 위조 신분증 즉시 폐기·교체"
          stampText="FORGED ID"
          peelDirection="diagonal"
        />
      </World>
    </Desk>
  );
};

// VOX_22 (B068-V01): "사진을 찍지 않고 신분증을 만들지 않으며 고향 말을 쓰지 않는다는 자신만의 철칙을 끝까지 지켰습니다."
export const VoxScene22: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb THREE_PROHIBITION_SHIELD
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <ScrapbookCollageAssembly
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          mainPhotoSrc={plateAsset('plate_22.jpg')}
          mainCaption="도주 3대 은신 철칙"
          mainTag="SURVIVAL CODE · 3금칙"
          secondCaption="사진·신분증·사투리 완전 금지"
          cutoutSrc={propAsset('prop_31_three_prohibitions.png')}
          cutoutCaption="3대 노출 차단 은신 수칙"
          cutoutBadge="노출 원천 차단"
          clippingSource="FUGITIVE CODE"
          clippingDate="1996-2005 RULE"
          clippingHeadline="사진·신분증·고향말 절대 금지"
          stampText="SEALED"
          variant="contradiction_versus"
        />
      </World>
    </Desk>
  );
};

// VOX_23 (B072-V01): "이천오년 일월 장시성 다위현에서 절도 혐의로 붙잡혔을 때도 그는 끝내 가명을 고수했습니다."
export const VoxScene23: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb ARREST_ALIAS_PERSISTENCE
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);
  const mainPlate = plateAsset('plate_23.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <PaperUnfoldCollage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          dossierTitle="장시성 다위현 절도 사건 입건부"
          dossierCode="JAN 2005 · 다위현 검거"
          leftPhotoSrc={mainPlate}
          leftCaption="단순 절도 공범 위장 진술"
          centerPhotoSrc={mainPlate}
          centerCaption="가명 저우전칭 끝까지 고수"
          rightCutoutSrc={propAsset('prop_22_inmate_award_badge.png')}
          rightCutoutCaption="가명 수감자 입소 등록표"
          rightHeadline="ARCHIVAL ENTRY · 가명 입건"
          rightBody="사형 중죄 은폐 목적 경미 절도 혐의 자처"
          dimensionLabel="절도 공범 가명 수감"
          stampText="BOOKED"
        />
      </World>
    </Desk>
  );
};

// VOX_24 (B075-V01): "사형에 처해질 살인마가 오히려 교도소를 가장 안전한 도피처로 삼는 기막힌 역설이 벌어진 것입니다."
export const VoxScene24: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb PRISON_SANCTUARY_PARADOX
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);
  const mainPlate = plateAsset('plate_24.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <TornPaperSplitReveal
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          coverPhotoSrc={mainPlate}
          coverTitle="간저우 교도소 모범 수감동"
          coverTag="2005~2009"
          revealPhotoSrc={mainPlate}
          revealTitle="A급 살인마의 교도소 도피처"
          revealTag="SANCTUARY PARADOX"
          cutoutSrc={propAsset('prop_18_iron_cell_bars.png')}
          cutoutCaption="교도소 철창 방패 역설"
          cutoutBadge="등잔 밑 은신"
          clippingHeadline="교도소를 도피처로 삼은 사형수"
          clippingBody="외부 수배망을 피해 국립 교도소 내부에 4년간 잠복"
          stampText="CONFIDENTIAL"
          peelDirection="left_to_right"
        />
      </World>
    </Desk>
  );
};

// VOX_25 (B079-V01): "당시 성 간 지문 전산망이 완전히 통합되지 않았다는 허점을 교묘하게 파고든 결과였습니다."
export const VoxScene25: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb OFFLINE_DB_GAP_EXPLOIT
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <CutoutPopOutStage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          photoSrc={plateAsset('plate_25.jpg')}
          photoCaption="성(省) 간 지문망 단절 허점"
          photoTag="2005 DB GAP · 오프라인 공백"
          cutoutSrc={propAsset('prop_32_paradox_scale.png')}
          cutoutCaption="사형 중죄 vs 7년형 위장 저울"
          cutoutBadge="전산 사각지대"
          clippingSource="SYSTEM AUDIT:"
          clippingDate="2005 ARCHIVE GAP"
          clippingHeadline="성(省) 간 지문 미연동 허점 악용"
          clippingBody="광둥성 수배 DB와 장시성 교도소 전산망 분리"
          highlightText="전산 미연동 공백"
          stampText="GAP EXPLOIT"
          layoutVariant="right_hero"
        />
      </World>
    </Desk>
  );
};

// VOX_26 (B084-V01): "높은 담장과 삼엄한 경비가 그를 세상으로부터가 아니라 경찰의 추적으로부터 지켜주고 있었던 셈입니다."
export const VoxScene26: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb WATCHTOWER_WALL_SHIELD
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <ScrapbookCollageAssembly
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          mainPhotoSrc={plateAsset('plate_26.jpg')}
          mainCaption="교도소 높은 담장과 감시탑"
          mainTag="WATCHTOWER · 역설의 방패"
          secondCaption="외부 경찰 수색망 차단 역설"
          cutoutSrc={propAsset('prop_14_prison_watchtower.png')}
          cutoutCaption="간저우 교도소 외곽 감시탑"
          cutoutBadge="완벽 은폐막"
          clippingSource="PRISON GUARD"
          clippingDate="2005-2009 WALL"
          clippingHeadline="추적을 막아준 교도소 높은 담장"
          stampText="SHIELDED"
          variant="diagonal_pair"
        />
      </World>
    </Desk>
  );
};

// VOX_27 (B091-V01): "그러나 이천구년 전국 교도소 재소자 지문을 중앙 전산망과 일괄 대조하는 사업이 시작되면서 완벽했던 은신처에 균열이 생겼습니다."
export const VoxScene27: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb CENTRAL_AFIS_SYNC_BREACH
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <LoupePhotoCutout
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          photoSrc={plateAsset('plate_27.jpg')}
          photoCaption="2009 전국 지문 중앙 대조"
          photoTag="CENTRAL AFIS · 본명 성루이룽"
          loupeFocusX={0.48}
          loupeFocusY={0.44}
          loupeLabel="중앙 서버 대조 · 성루이룽 특정"
          cutoutSrc={propAsset('prop_15_afis_scanner_loupe.png')}
          cutoutCaption="공안부 지문 광학 감식 루페"
          cutoutBadge="신원 일치"
          clippingHeadline="전국 지문 통합 대조로 본명 특정"
          clippingBody="재소자 지문 중앙 서버 전송 직후 적색 경보 발령"
          stampText="MATCHED"
        />
      </World>
    </Desk>
  );
};

// VOX_28 (B098-V01): "소식을 접한 포산시 공안국 전담 수사팀은 즉시 장시성 간저우 교도소로 급파되었습니다."
export const VoxScene28: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb SATELLITE_DETECTIVE_DISPATCH
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  return (
    <AbsoluteFill style={{backgroundColor: '#0A0D12'}}>
      <GeoJson3DMapStage
        plateSrc={plateAsset('cheng_sat_08_ningbo_z15.jpg')}
        plateMeta={CHENGRUILONG_PLATES.cheng_sat_08_ningbo_z15}
        startFocusLonLat={CHENGRUILONG_LANDMARKS.detectiveArrivalGate}
        endFocusLonLat={CHENGRUILONG_LANDMARKS.specialInterrogationWing}
        startZoom={1.15}
        endZoom={1.78}
        startPitch={21}
        endPitch={49}
        startBearing={-8}
        endBearing={22}
        flyStartFrame={t1}
        flyEndFrame={t3}
        showOpticalLoupe={true}
        loupeZoom={4}
        satLoupe={{
          targetLon: CHENGRUILONG_LANDMARKS.specialInterrogationWing[0],
          targetLat: CHENGRUILONG_LANDMARKS.specialInterrogationWing[1],
          screenX: 1618,
          screenY: 226,
          diameter: 228,
          zoomFactor: 4,
          progress: p12(f, t2 + 4, 18),
          loupePlateSrc: loupeAsset('cheng_sat_08_loupe.jpg'),
          loupePlateMeta: CHENGRUILONG_PLATES.cheng_sat_08_ningbo_z15,
          labelTitle: '간저우 합동 심문동 4X',
          labelSub: '포산 전담팀 직통 급파 완료',
        }}
        polygons={[
          {
            id: 'poly-28',
            coordinates: CHENGRUILONG_GEO_ROUTES.interrogationBlockPolygon,
            fillColor: 'rgba(239, 68, 68, 0.18)',
            strokeColor: '#38BDF8',
            enterFrame: t1,
          },
        ]}
        routes={[
          {
            id: 'route-28',
            coordinates: CHENGRUILONG_GEO_ROUTES.foshanDetectiveCorridorRoute,
            color: '#EF4444',
            widthPx: 6,
            drawStartFrame: t1,
            drawEndFrame: t3,
          },
        ]}
        pins={[
          {
            id: 'pin-28-1',
            lonLat: CHENGRUILONG_LANDMARKS.detectiveArrivalGate,
            label: '포산시 공안국 전담 수사팀 도착',
            sublabel: '11년 추적 전담 형사팀 긴급 급파',
            appearFrame: t1,
            color: '#38BDF8',
            dx: -166,
            dy: -82,
            align: 'right',
          },
          {
            id: 'pin-28-2',
            lonLat: CHENGRUILONG_LANDMARKS.specialInterrogationWing,
            label: '장시성 간저우 교도소 합동 심문실',
            sublabel: '최종 대면 심문 · 신원 확인 완료',
            appearFrame: t2,
            color: '#EF4444',
            dx: 118,
            dy: 80,
            align: 'left',
          },
        ]}
        headerBadge="2009.05 · 포산시 공안국 → 간저우 교도소 긴급 급파 노선"
        headerTitle="지문 일치 즉시 장시성 간저우 교도소로 급파된 포산 전담 수사팀"
      />
    </AbsoluteFill>
  );
};

// VOX_29 (B102-V01): "고향 사투리로 건넨 짧은 질문 하나에 십삼 년간 쌓아 올린 가짜 신분의 벽이 단숨에 무너져 내렸습니다."
export const VoxScene29: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb DIALECT_SHOCK_BREACH
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <CutoutPopOutStage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          photoSrc={plateAsset('plate_29.jpg')}
          photoCaption="광둥 사투리 기습 심문"
          photoTag="DIALECT SHOCK · 위장 붕괴"
          cutoutSrc={propAsset('prop_25_urgent_dispatch.png')}
          cutoutCaption="포산 전담팀 대면 심문 조서"
          cutoutBadge="사투리 타격"
          clippingSource="INTERROGATION:"
          clippingDate="2009.05 GANZHOU"
          clippingHeadline="고향 사투리 질문에 가명 붕괴"
          clippingBody="13년 동안 봉인했던 모어 반응으로 심리 방어선 와해"
          highlightText="가짜 신분 벽 붕괴"
          stampText="CRACKED"
          layoutVariant="center_split"
        />
      </World>
    </Desk>
  );
};

// VOX_30 (B106-V01): "성루이룽의 자백으로 십 년 넘게 미제로 남아 있던 전국 각지의 살인 사건들이 하나의 퍼즐처럼 맞춰졌습니다."
export const VoxScene30: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb COLD_CASE_PUZZLE_LINK
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);
  const mainPlate = plateAsset('plate_30.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <PaperUnfoldCollage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          dossierTitle="장기 미제 살인 병합부"
          dossierCode="10 PROVINCES · 미제 병합"
          leftPhotoSrc={mainPlate}
          leftCaption="10개 성 미제 사건 대조"
          centerPhotoSrc={mainPlate}
          centerCaption="탄도·지문 퍼즐 완결"
          rightCutoutSrc={propAsset('prop_27_concealed_pistol.png')}
          rightCutoutCaption="연쇄 총기 탄도 일치표"
          rightHeadline="ARCHIVAL ENTRY · 미제 완결"
          rightBody="광둥·광시·후난·충칭 미제 사건 해결"
          dimensionLabel="10개 성 미제 병합"
          stampText="SOLVED"
        />
      </World>
    </Desk>
  );
};

// VOX_31 (B110-V01): "수사팀은 그의 진술을 토대로 과거 범행 현장을 일일이 다시 찾아가 숨겨진 물증과 기록을 교차 검증했습니다."
export const VoxScene31: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb FORENSIC_SCENE_REVERIFY
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <LoupePhotoCutout
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          photoSrc={plateAsset('plate_31.jpg')}
          photoCaption="과거 범행 현장 교차 검증"
          photoTag="RE-VERIFICATION · 현장 실사"
          loupeFocusX={0.38}
          loupeFocusY={0.54}
          loupeLabel="현장 유류 흔적·자백 교차 대조"
          cutoutSrc={propAsset('prop_33_afis_upload_card.png')}
          cutoutCaption="11년 누적 감식 대조 원부"
          cutoutBadge="현장 검증"
          clippingHeadline="자백 진술·현장 물증 정밀 대조"
          clippingBody="전국 과거 범행지 재답사 및 법의학 물증 확증"
          stampText="REVERIFIED"
        />
      </World>
    </Desk>
  );
};

// VOX_32 (B114-V01): "수백 권에 달하는 수사 기록과 현장 감식 자료가 마침내 단 한 사람의 이름을 향해 모이기 시작했습니다."
export const VoxScene32: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb ARCHIVE_TRACE_CONVERGENCE
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);
  const mainPlate = plateAsset('plate_32.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <TornPaperSplitReveal
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          coverPhotoSrc={mainPlate}
          coverTitle="수백 권의 장기 미제 수사철"
          coverTag="MAY 2009"
          revealPhotoSrc={mainPlate}
          revealTitle="단일 주범 성루이룽 귀결"
          revealTag="SINGLE PERPETRATOR"
          cutoutSrc={propAsset('prop_06_cold_storage_ledger.png')}
          cutoutCaption="장기 보존 사건 원본 대장"
          cutoutBadge="증거 총집결"
          clippingHeadline="수백 권 수사 기록 단일 피고인 수렴"
          clippingBody="10개 성 공안청 감식 자료 공소장 통합 편철"
          stampText="CONVERGED"
          peelDirection="top_to_bottom"
        />
      </World>
    </Desk>
  );
};

// VOX_33 (B118-V01): "마침내 광둥성 포산으로 압송되던 날 역 플랫폼에는 삼엄한 무장 병력과 수많은 취재진이 몰려들었습니다."
export const VoxScene33: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb EXTRADITION_PLATFORM_CORDON
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <ScrapbookCollageAssembly
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          mainPhotoSrc={plateAsset('plate_33.jpg')}
          mainCaption="광둥성 포산역 무장 압송"
          mainTag="EXTRADITION · 특수 호송"
          secondCaption="플랫폼 특경대 무장 경계선"
          cutoutSrc={propAsset('prop_12_green_train_ticket.png')}
          cutoutCaption="간저우-포산 특별 호송 열차표"
          cutoutBadge="무장 압송"
          clippingSource="TRANSIT CORDONS"
          clippingDate="MAY 2009 FOSHAN"
          clippingHeadline="포산역 플랫폼 특경대 무장 압송"
          stampText="EXTRADITED"
          variant="video_focus"
        />
      </World>
    </Desk>
  );
};

// VOX_34 (B122-V01): "동료를 잃고 십일 년을 기다려온 포산의 경찰관들은 압송되어 오는 그의 모습을 말없이 지켜보았습니다."
export const VoxScene34: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb FALLEN_OFFICER_MEMORIAL_AXIS
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);
  const mainPlate = plateAsset('plate_34.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <PaperUnfoldCollage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          dossierTitle="포산 공안국 순직 경찰관 추모록"
          dossierCode="1998~2009 · 11년의 약속"
          leftPhotoSrc={mainPlate}
          leftCaption="순직 동료에게 바치는 검거 보고"
          centerPhotoSrc={mainPlate}
          centerCaption="11년을 기다린 포산 동료 경관들"
          rightCutoutSrc={propAsset('prop_30_fallen_badges.png')}
          rightCutoutCaption="순직 경찰관 4인 추모 배지"
          rightHeadline="ARCHIVAL ENTRY · 순직 동료 추모"
          rightBody="전우의 영정 앞에 바친 11년 만의 범인 압송"
          dimensionLabel="순직 경관 4인 추모"
          stampText="HONORED"
        />
      </World>
    </Desk>
  );
};

// VOX_35 (B126-V01): "이천십년 포산시 중급인민법원에서 열린 공판에서 피고인석에 선 성루이룽은 기소된 혐의 대부분을 인정했습니다."
export const VoxScene35: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb COURTROOM_DEFENDANT_GAZE
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <LoupePhotoCutout
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          photoSrc={plateAsset('plate_35.jpg')}
          photoCaption="포산 중급인민법원 공판"
          photoTag="2010 TRIAL · 피고인석"
          loupeFocusX={0.56}
          loupeFocusY={0.42}
          loupeLabel="법정 피고인석 성루이룽 시선"
          cutoutSrc={propAsset('prop_17_steel_handcuffs.png')}
          cutoutCaption="법정 구속 철제 수갑"
          cutoutBadge="혐의 시인"
          clippingHeadline="포산 중급법원 공판 혐의 인정"
          clippingBody="기소된 연쇄 무장 강도·살인 공소사실 전면 시인"
          stampText="INDICTED"
        />
      </World>
    </Desk>
  );
};

// VOX_36 (B130-V01): "재판부는 극악무도한 연쇄 살인과 무장 강도 죄책을 물어 그에게 법정 최고형인 사형을 선고했습니다."
export const VoxScene36: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb CAPITAL_VERDICT_PRONOUNCEMENT
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <CutoutPopOutStage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          photoSrc={plateAsset('plate_36.jpg')}
          photoCaption="법정 최고형 사형 선고"
          photoTag="DEATH SENTENCE · 정치권리 박탈"
          cutoutSrc={propAsset('prop_19_court_gavel_verdict.png')}
          cutoutCaption="사형 선고 법봉 및 판결문"
          cutoutBadge="사형 판결"
          clippingSource="VERDICT SHEET:"
          clippingDate="2010 FOSHAN COURT"
          clippingHeadline="연쇄 살인·무장 강도 사형 선고"
          clippingBody="13명 살해 및 다수 총기 강도 병합 법정 최고형 판결"
          highlightText="법정 최고형 사형"
          stampText="SENTENCED"
          layoutVariant="left_hero"
        />
      </World>
    </Desk>
  );
};

// VOX_37 (B134-V01): "최고인민법원의 사형 복핵 승인이 내려진 뒤 이천십년 십일월 이일 성루이룽에 대한 형이 최종 집행되었습니다."
export const VoxScene37: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb SUPREME_EXECUTION_ORDER
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);
  const mainPlate = plateAsset('plate_37.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <TornPaperSplitReveal
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          coverPhotoSrc={mainPlate}
          coverTitle="최고인민법원 사형 복핵 재가"
          coverTag="NOV 2010"
          revealPhotoSrc={mainPlate}
          revealTitle="2010.11.02 사형 최종 집행"
          revealTag="EXECUTION COMPLETED"
          cutoutSrc={propAsset('prop_34_supreme_execution_order.png')}
          cutoutCaption="최고인민법원 사형 집행 명령서"
          cutoutBadge="집행 완료"
          clippingHeadline="2010년 11월 2일 사형 집행 완료"
          clippingBody="최고인민법원 최종 복핵 승인 직후 형 집행 종결"
          stampText="EXECUTED"
          peelDirection="diagonal"
        />
      </World>
    </Desk>
  );
};

// VOX_38 (B138-V01): "열세 명의 목숨을 앗아간 피의 도주극은 이렇게 십삼 년 만에 마침표를 찍었습니다."
export const VoxScene38: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb FUGITIVE_ARC_TERMINATION
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <ScrapbookCollageAssembly
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          mainPhotoSrc={plateAsset('plate_38.jpg')}
          mainCaption="13년 도주극 최종 종결"
          mainTag="1996~2010 · 사건 종결"
          secondCaption="A급 지명수배령 공식 해제"
          cutoutSrc={propAsset('prop_23_red_warrant_seal.png')}
          cutoutCaption="수배 해제 및 사건 종결 직인"
          cutoutBadge="수배 종료"
          clippingSource="FINAL CLOSURE"
          clippingDate="NOV 02 2010"
          clippingHeadline="13년 피의 도주극 최종 마침표"
          stampText="CLOSED"
          variant="pinboard_web"
        />
      </World>
    </Desk>
  );
};

// VOX_39 (B142-V01): "완벽한 위장도 끝까지 포기하지 않는 수사관들의 집념과 과학 수사의 그물망을 피할 수는 없었습니다."
export const VoxScene39: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb DETECTIVE_TENACITY_CHRONICLE
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);
  const mainPlate = plateAsset('plate_39.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <PaperUnfoldCollage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          dossierTitle="포산 전담팀 11년 추적 수사백서"
          dossierCode="1998~2009 · 과학 수사"
          leftPhotoSrc={mainPlate}
          leftCaption="수사관들의 끝없는 추적 집념"
          centerPhotoSrc={mainPlate}
          centerCaption="전국 생체 지문망이 거둔 승리"
          rightCutoutSrc={propAsset('prop_07_patrol_motorcycle_badge.png')}
          rightCutoutCaption="포산 공안 기동 순찰 흉장"
          rightHeadline="ARCHIVAL ENTRY · 집념과 과학수사"
          rightBody="포기하지 않는 형사들의 추적과 과학수사 통합망"
          dimensionLabel="11년 집념의 추적"
          stampText="JUSTICE"
        />
      </World>
    </Desk>
  );
};

// VOX_40 (B146-V01): "성루이룽 사건은 중국 범죄사상 가장 집요했던 추적극이자 법망은 결코 뚫리지 않는다는 사실을 남긴 사건으로 기록되었습니다."
export const VoxScene40: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb FORENSIC_ARCHIVE_SEAL
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  const cam = camAt(f, [
    {at: 0, pose: {x: 960, y: 540, z: 1.0, r: 0}},
    {at: t3, pose: {x: 960, y: 540, z: 1.02, r: 0}},
  ]);

  return (
    <Desk>
      <World cam={cam}>
        <LoupePhotoCutout
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          photoSrc={plateAsset('plate_40.jpg')}
          photoCaption="성루이룽 사건 영구 보존"
          photoTag="ARCHIVE SEALED · 사건 종결"
          loupeFocusX={0.42}
          loupeFocusY={0.5}
          loupeLabel="공안부 영구 보존 사건 기록함"
          cutoutSrc={propAsset('prop_20_case_archive_box.png')}
          cutoutCaption="영구 보존 사건 기록 보관함"
          cutoutBadge="영구 봉인"
          clippingHeadline="중국 범죄사 최장기 추적극 봉인"
          clippingBody="1996~2010 성루이룽 연쇄 살인 사건 전권 영구 보존"
          stampText="ARCHIVED"
        />
      </World>
    </Desk>
  );
};
