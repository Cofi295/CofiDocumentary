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

// VOX_01 (B002-V01): "교도관에게 이끌려 들어온 한 남자가 철제 의자 한가운데에 천천히 걸터앉았습니다."
export const VoxScene01: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb INTERROGATION_CHAIR_LOCK
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
          photoSrc={plateAsset('plate_01.jpg')}
          photoCaption="간저우 특별 심문실"
          photoTag="2009.05 · 특별 심문실"
          cutoutSrc={propAsset('prop_01_iron_chair.png')}
          cutoutCaption="중앙 고정 철제 의자"
          cutoutBadge="심문 구속구"
          clippingSource="EXHIBIT A:"
          clippingDate="2009.05 GANZHOU"
          clippingHeadline="특별 심문실 피의자 착석"
          clippingBody="장시성 간저우 교도소 합동 심문실 기록"
          highlightText="철제 의자 격리 심문"
          stampText="RECEIVED"
          layoutVariant="left_hero"
        />
      </World>
    </Desk>
  );
};

// VOX_02 (B007-V01): "모범수로 감형까지 받은 터라 만기 출소까지는 불과 1년 남짓한 기간만 남아 있었습니다."
export const VoxScene02: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb SENTENCE_COUNTDOWN_AXIS
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
  const mainPlate = plateAsset('plate_02.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <PaperUnfoldCollage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          dossierTitle="간저우 교도소 모범수 감형 심사부"
          dossierCode="2005~2010 · 잔여 1년"
          leftPhotoSrc={mainPlate}
          leftCaption="가명 저우전칭 복역 기록"
          centerPhotoSrc={mainPlate}
          centerCaption="만기 출소 12개월 전"
          rightCutoutSrc={propAsset('prop_21_commutation_seal.png')}
          rightCutoutCaption="모범수 감형 승인 인장"
          rightHeadline="ARCHIVAL ENTRY · 잔여 형기 1년"
          rightBody="모범 수감자 표창 및 형기 단축 기록"
          dimensionLabel="출소 잔여 12개월"
          stampText="CONFIDENTIAL"
        />
      </World>
    </Desk>
  );
};

// VOX_03 (B012-V01): "그도 그럴 것이 지난 4년 동안 간저우 교도소 안에서 그는 누구보다 성실한 수감자였습니다."
export const VoxScene03: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb SATELLITE_PRISON_GRID_LOCK
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  return (
    <AbsoluteFill style={{backgroundColor: '#0A0D12'}}>
      <GeoJson3DMapStage
        plateSrc={plateAsset('cheng_sat_01_ganzhou_z14.jpg')}
        plateMeta={CHENGRUILONG_PLATES.cheng_sat_01_ganzhou_z14}
        startFocusLonLat={CHENGRUILONG_LANDMARKS.ganzhouPrisonGate}
        endFocusLonLat={CHENGRUILONG_LANDMARKS.ganzhouPublicSecurityBureau}
        startZoom={1.14}
        endZoom={1.76}
        startPitch={18}
        endPitch={46}
        startBearing={-16}
        endBearing={12}
        flyStartFrame={t1}
        flyEndFrame={t3}
        showOpticalLoupe={true}
        loupeZoom={4}
        satLoupe={{
          targetLon: CHENGRUILONG_LANDMARKS.ganzhouCapture2009[0],
          targetLat: CHENGRUILONG_LANDMARKS.ganzhouCapture2009[1],
          screenX: 1610,
          screenY: 226,
          diameter: 228,
          zoomFactor: 4,
          progress: p12(f, t2 + 4, 18),
          loupePlateSrc: loupeAsset('cheng_sat_01_loupe.jpg'),
          loupePlateMeta: CHENGRUILONG_PLATES.cheng_sat_01_ganzhou_z14,
          labelTitle: '간저우 교도소 수감 구역 4X',
          labelSub: '2005~2009 모범수 위장 복역 지점',
        }}
        polygons={[
          {
            id: 'poly-3',
            coordinates: CHENGRUILONG_GEO_ROUTES.ganzhouPrisonPerimeter,
            fillColor: 'rgba(239, 68, 68, 0.18)',
            strokeColor: '#EF4444',
            enterFrame: t1,
          },
        ]}
        routes={[
          {
            id: 'route-3',
            coordinates: CHENGRUILONG_GEO_ROUTES.ganzhouPrisonToBureauRoute,
            color: '#F59E0B',
            widthPx: 6,
            drawStartFrame: t1,
            drawEndFrame: t3,
          },
        ]}
        pins={[
          {
            id: 'pin-3-1',
            lonLat: CHENGRUILONG_LANDMARKS.ganzhouPrisonGate,
            label: '간저우 교도소 감방동',
            sublabel: '가명 저우전칭 4년 모범 수감지',
            appearFrame: t1,
            color: '#EF4444',
            dx: -165,
            dy: -82,
            align: 'right',
          },
          {
            id: 'pin-3-2',
            lonLat: CHENGRUILONG_LANDMARKS.ganzhouPublicSecurityBureau,
            label: '장시성 공안청 호송 축선',
            sublabel: '심문실 정밀 대조 구역',
            appearFrame: t2,
            color: '#38BDF8',
            dx: 118,
            dy: 76,
            align: 'left',
          },
        ]}
        headerBadge="2005~2009 · 장시성 간저우 교도소 3D 위성 구역도"
        headerTitle="4년간 모범수로 위장 복역한 간저우 교도소 정밀 지리 추적"
      />
    </AbsoluteFill>
  );
};

// VOX_04 (B015-V01): "생체 지문 데이터베이스 정밀 대조 시스템이 가동되면서 이 조용한 모범수의 진짜 얼굴이 드러나기 시작했습니다."
export const VoxScene04: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb BIOMETRIC_MINUTIAE_MATCH
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
          photoSrc={plateAsset('plate_04.jpg')}
          photoCaption="생체 지문 정밀 대조"
          photoTag="AFIS · 특징점 16개 일치"
          loupeFocusX={0.44}
          loupeFocusY={0.46}
          loupeLabel="지문 융선 2.6X 정밀 감정"
          cutoutSrc={propAsset('prop_03_fingerprint_ten_card.png')}
          cutoutCaption="10지 생체 지문 원판"
          cutoutBadge="특징점 일치"
          clippingHeadline="포산 현장 유류 지문 100% 합치"
          clippingBody="모범수 저우전칭과 수배범 성루이룽 동일인 판정"
          stampText="VERIFIED"
        />
      </World>
    </Desk>
  );
};

// VOX_05 (B017-V01): "가명 뒤에 숨어 있던 그의 정체는 중국 공안부 A급 수배범 성루이룽이었습니다."
export const VoxScene05: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb CLASS_A_WARRANT_UNSEAL
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
  const mainPlate = plateAsset('plate_05.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <TornPaperSplitReveal
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          coverPhotoSrc={mainPlate}
          coverTitle="위조 신분 저우전칭"
          coverTag="A급 수배 대조"
          revealPhotoSrc={mainPlate}
          revealTitle="공안부 A급 수배범 성루이룽"
          revealTag="CLASS-A WARRANT"
          cutoutSrc={propAsset('prop_04_class_a_warrant.png')}
          cutoutCaption="공안부 A급 지명수배령"
          cutoutBadge="특급 수배"
          clippingHeadline="13년 은폐 본명 성루이룽 폭로"
          clippingBody="중국 공안부 A급 지명수배 원부 대조 완료"
          stampText="TOP SECRET"
          peelDirection="left_to_right"
        />
      </World>
    </Desk>
  );
};

// VOX_06 (B020-V01): "경찰관 네 명을 포함해 무려 열세 명을 살해한 연쇄 살인마의 실체가 마침내 세상 밖으로 드러난 것입니다."
export const VoxScene06: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb SERIAL_VICTIM_TOLL_MATRIX
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
          mainPhotoSrc={plateAsset('plate_06.jpg')}
          mainCaption="희생자 총 13명 집계"
          mainTag="1996~2005 · 연쇄 참극"
          secondCaption="순직 경찰관 4명 포함"
          cutoutSrc={propAsset('prop_24_shackles_dossier.png')}
          cutoutCaption="중범죄 연쇄 살인 병합 철"
          cutoutBadge="13명 살해"
          clippingSource="CASE LEDGER"
          clippingDate="1996-2005 ARCHIVE"
          clippingHeadline="경찰 4명 포함 13명 살해 확인"
          stampText="ARCHIVE"
          variant="diagonal_pair"
        />
      </World>
    </Desk>
  );
};

// VOX_07 (B023-V01): "자신의 진짜 이름을 들은 순간 그의 눈동자가 미세하게 흔들렸고 손끝은 가늘게 떨리기 시작했습니다."
export const VoxScene07: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb PSYCHOLOGICAL_TREMOR_SPIKE
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
          photoSrc={plateAsset('plate_07.jpg')}
          photoCaption="심문실 미세 동공 반응"
          photoTag="PSYCHOLOGY · 방어기제 붕괴"
          loupeFocusX={0.52}
          loupeFocusY={0.38}
          loupeLabel="본명 호명 직후 동공·손끝 떨림"
          cutoutSrc={propAsset('prop_02_inmate_card.png')}
          cutoutCaption="수감자 신분 대조 카드"
          cutoutBadge="심리 동요"
          clippingHeadline="본명 호명 순간 미세 떨림 포착"
          clippingBody="13년 위장 신분 붕괴 직전 생리 반응 기록"
          stampText="OBSERVED"
        />
      </World>
    </Desk>
  );
};

// VOX_08 (B026-V01): "긴 침묵 끝에 담배 한 개비를 요청한 그는 마침내 모든 것을 체념한 듯 입을 열었습니다."
export const VoxScene08: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb CONFESSION_COLLAPSE_PIVOT
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
          photoSrc={plateAsset('plate_08.jpg')}
          photoCaption="담배 한 개비와 자백"
          photoTag="CONFESSION · 전면 실토"
          cutoutSrc={propAsset('prop_16_guangdong_cigarette_pack.png')}
          cutoutCaption="심문실 지급 광둥 담배"
          cutoutBadge="자백 전환점"
          clippingSource="EXHIBIT B:"
          clippingDate="2009.05 INTERROGATION"
          clippingHeadline="침묵 끝 담배 요청 후 전면 자백"
          clippingBody="13년 도주 행적 및 미제 살인 자백 개시"
          highlightText="전면 자백 개시"
          stampText="CONFESSED"
          layoutVariant="right_hero"
        />
      </World>
    </Desk>
  );
};

// VOX_09 (B031-V01): "그 첫 번째 참극은 천구백구십육년 오월 광둥성 포산시 난하이구에서 벌어졌습니다."
export const VoxScene09: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb SATELLITE_CRIME_ORIGIN_PIN
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  return (
    <AbsoluteFill style={{backgroundColor: '#0A0D12'}}>
      <GeoJson3DMapStage
        plateSrc={plateAsset('cheng_sat_02_foshan_z15.jpg')}
        plateMeta={CHENGRUILONG_PLATES.cheng_sat_02_foshan_z15}
        startFocusLonLat={CHENGRUILONG_LANDMARKS.foshanNanhaiStart}
        endFocusLonLat={CHENGRUILONG_LANDMARKS.foshanKaiyuanCheckpoint}
        startZoom={1.15}
        endZoom={1.8}
        startPitch={22}
        endPitch={48}
        startBearing={14}
        endBearing={-18}
        flyStartFrame={t1}
        flyEndFrame={t3}
        showOpticalLoupe={true}
        loupeZoom={4}
        satLoupe={{
          targetLon: CHENGRUILONG_LANDMARKS.foshanOrigin1996[0],
          targetLat: CHENGRUILONG_LANDMARKS.foshanOrigin1996[1],
          screenX: 1615,
          screenY: 232,
          diameter: 230,
          zoomFactor: 4,
          progress: p12(f, t2 + 4, 18),
          loupePlateSrc: loupeAsset('cheng_sat_02_loupe.jpg'),
          loupePlateMeta: CHENGRUILONG_PLATES.cheng_sat_02_foshan_z15,
          labelTitle: '포산 난하이구 현장 4X',
          labelSub: '1996.05 연쇄 참극 시작점',
        }}
        polygons={[
          {
            id: 'poly-9',
            coordinates: CHENGRUILONG_GEO_ROUTES.foshanKaiyuanCordonPolygon,
            fillColor: 'rgba(239, 68, 68, 0.18)',
            strokeColor: '#EF4444',
            enterFrame: t1,
          },
        ]}
        routes={[
          {
            id: 'route-9',
            coordinates: CHENGRUILONG_GEO_ROUTES.foshanKaiyuanPatrolRoute,
            color: '#EF4444',
            widthPx: 6,
            drawStartFrame: t1,
            drawEndFrame: t3,
          },
        ]}
        pins={[
          {
            id: 'pin-9-1',
            lonLat: CHENGRUILONG_LANDMARKS.foshanNanhaiStart,
            label: '포산시 난하이구 사건 현장',
            sublabel: '1996.05 첫 무장 강도·살인 발생지',
            appearFrame: t1,
            color: '#EF4444',
            dx: -172,
            dy: -84,
            align: 'right',
          },
          {
            id: 'pin-9-2',
            lonLat: CHENGRUILONG_LANDMARKS.foshanKaiyuanCheckpoint,
            label: '외곽 도주 연결 도로망',
            sublabel: '공안 초기 봉쇄선 돌파 지점',
            appearFrame: t2,
            color: '#F59E0B',
            dx: 122,
            dy: 78,
            align: 'left',
          },
        ]}
        headerBadge="1996.05 · 광둥성 포산시 난하이구 3D 위성 지도"
        headerTitle="성루이룽 13년 연쇄 살인극의 출발점 포산 난하이구 현장"
      />
    </AbsoluteFill>
  );
};

// VOX_10 (B038-V01): "이듬해인 천구백구십칠년 삼월 성루이룽 일당은 광둥성 롄저우시의 한 우체국 저축소를 새로운 표적으로 삼았습니다."
export const VoxScene10: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb SATELLITE_TARGET_SURVEILLANCE
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  return (
    <AbsoluteFill style={{backgroundColor: '#0A0D12'}}>
      <GeoJson3DMapStage
        plateSrc={plateAsset('cheng_sat_07_lianzhou_z14.jpg')}
        plateMeta={CHENGRUILONG_PLATES.cheng_sat_07_lianzhou_z14}
        startFocusLonLat={CHENGRUILONG_LANDMARKS.lianzhouTownPostOffice}
        endFocusLonLat={CHENGRUILONG_LANDMARKS.lianzhouBankBranch}
        startZoom={1.14}
        endZoom={1.74}
        startPitch={20}
        endPitch={50}
        startBearing={-24}
        endBearing={8}
        flyStartFrame={t1}
        flyEndFrame={t3}
        showOpticalLoupe={true}
        loupeZoom={4}
        satLoupe={{
          targetLon: CHENGRUILONG_LANDMARKS.lianzhouBankBranch[0],
          targetLat: CHENGRUILONG_LANDMARKS.lianzhouBankBranch[1],
          screenX: 1605,
          screenY: 228,
          diameter: 226,
          zoomFactor: 4,
          progress: p12(f, t2 + 4, 18),
          loupePlateSrc: loupeAsset('cheng_sat_07_loupe.jpg'),
          loupePlateMeta: CHENGRUILONG_PLATES.cheng_sat_07_lianzhou_z14,
          labelTitle: '롄저우 우체국 저축소 4X',
          labelSub: '1997.03 제2차 무장 습격 표적',
        }}
        polygons={[
          {
            id: 'poly-10',
            coordinates: CHENGRUILONG_GEO_ROUTES.lianzhouWatchZonePolygon,
            fillColor: 'rgba(239, 68, 68, 0.18)',
            strokeColor: '#F59E0B',
            enterFrame: t1,
          },
        ]}
        routes={[
          {
            id: 'route-10',
            coordinates: CHENGRUILONG_GEO_ROUTES.lianzhouPostBankSurveillanceRoute,
            color: '#EF4444',
            widthPx: 6,
            drawStartFrame: t1,
            drawEndFrame: t3,
          },
        ]}
        pins={[
          {
            id: 'pin-10-1',
            lonLat: CHENGRUILONG_LANDMARKS.lianzhouTownPostOffice,
            label: '광둥성 롄저우시 우체국 저축소',
            sublabel: '1997.03 사전 치밀 답사 표적',
            appearFrame: t1,
            color: '#EF4444',
            dx: -168,
            dy: -80,
            align: 'right',
          },
          {
            id: 'pin-10-2',
            lonLat: CHENGRUILONG_LANDMARKS.lianzhouBankBranch,
            label: '야간 침투·도주 골목 축선',
            sublabel: '현금 수송 동선 사전 잠복로',
            appearFrame: t2,
            color: '#38BDF8',
            dx: 116,
            dy: 82,
            align: 'left',
          },
        ]}
        headerBadge="1997.03 · 광둥성 롄저우시 우체국 저축소 3D 위성 추적"
        headerTitle="치밀한 사전 답사로 노린 롄저우 우체국 저축소 습격 동선"
      />
    </AbsoluteFill>
  );
};

// VOX_11 (B041-V01): "천구백구십팔년 오월 포산시 카이위안 거리에서 순찰 중이던 경찰관 두 명이 수상한 행적의 그를 불러 세웠습니다."
export const VoxScene11: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb MOTORCYCLE_PATROL_INTERCEPT
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
          mainPhotoSrc={plateAsset('plate_11.jpg')}
          mainCaption="포산 카이위안 거리 검문"
          mainTag="MAY 1998 · FOSHAN"
          secondCaption="순찰 경관 2명 불심검문"
          cutoutSrc={propAsset('prop_26_kaiyuan_motorcycle.png')}
          cutoutCaption="카이위안 기동 순찰 오토바이"
          cutoutBadge="검문 정지"
          clippingSource="PATROL LOG"
          clippingDate="MAY 22 1998"
          clippingHeadline="카이위안 거리 순찰 경관 2명 검문"
          stampText="ARCHIVE"
          variant="video_focus"
        />
      </World>
    </Desk>
  );
};

// VOX_12 (B043-V01): "신분증 제시를 요구받자 성루이룽은 품속에서 권총을 뽑아 들고 그 자리에서 경찰관들을 향해 방아쇠를 당겼습니다."
export const VoxScene12: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb POINT_BLANK_BALLISTIC_CONE
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
          photoSrc={plateAsset('plate_12.jpg')}
          photoCaption="카이위안 영거리 총격"
          photoTag="BALLISTICS · 54식 권총"
          cutoutSrc={propAsset('prop_08_brass_shell_casing.png')}
          cutoutCaption="현장 수거 7.62mm 탄피"
          cutoutBadge="탄도 증거"
          clippingSource="EXHIBIT C:"
          clippingDate="1998.05 BALLISTICS"
          clippingHeadline="검문 직후 은닉 권총 기습 발포"
          clippingBody="포산 카이위안 노상 탄피 및 강선 감식 기록"
          highlightText="영거리 기습 격발"
          stampText="EVIDENCE"
          layoutVariant="center_split"
        />
      </World>
    </Desk>
  );
};

// VOX_13 (B045-V01): "도심 한복판에서 경찰관이 피살되자 중국 공안부는 전국에 긴급 수배령을 내리고 대대적인 포위망을 펼쳤습니다."
export const VoxScene13: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb NATIONAL_MANHUNT_ALERT
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
  const mainPlate = plateAsset('plate_13.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <PaperUnfoldCollage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          dossierTitle="공안부 전국 긴급 수배 전문"
          dossierCode="1998.05 · 전국 봉쇄"
          leftPhotoSrc={mainPlate}
          leftCaption="광둥성 전역 검문소 배치"
          centerPhotoSrc={mainPlate}
          centerCaption="도심 외곽 무장 봉쇄선"
          rightCutoutSrc={propAsset('prop_05_urgent_telegram.png')}
          rightCutoutCaption="공안부 긴급 전문 전보"
          rightHeadline="ARCHIVAL ENTRY · 전국 수배령"
          rightBody="경찰관 피살 직후 광역 검문 포위망 가동"
          dimensionLabel="광역 봉쇄망 가동"
          stampText="URGENT"
        />
      </World>
    </Desk>
  );
};

// VOX_14 (B046-V01): "공범 란가오싱은 곧바로 체포되었지만 성루이룽은 포위망의 빈틈을 뚫고 어둠 속으로 유유히 사라졌습니다."
export const VoxScene14: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb CORDON_BREACH_DIVERGENCE
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
  const mainPlate = plateAsset('plate_14.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <TornPaperSplitReveal
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          coverPhotoSrc={mainPlate}
          coverTitle="공범 란가오싱 현장 체포"
          coverTag="MAY 1998"
          revealPhotoSrc={mainPlate}
          revealTitle="주범 성루이룽 포위망 이탈"
          revealTag="CORDON BREACHED"
          cutoutSrc={propAsset('prop_29_ambush_radius.png')}
          cutoutCaption="야간 포위망 돌파 반경"
          cutoutBadge="단독 도주"
          clippingHeadline="공범 검거 직후 야간 사각지대 이탈"
          clippingBody="검문 포위망 빈틈 돌파 후 단독 잠적"
          stampText="BREACHED"
          peelDirection="top_to_bottom"
        />
      </World>
    </Desk>
  );
};

// VOX_15 (B048-V01): "경찰의 추격을 따돌린 그는 광시 구이린으로 숨어들어 또다시 무장 강도 행각을 벌였습니다."
export const VoxScene15: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb SATELLITE_MOUNTAIN_ESCAPE_ROUTE
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  return (
    <AbsoluteFill style={{backgroundColor: '#0A0D12'}}>
      <GeoJson3DMapStage
        plateSrc={plateAsset('cheng_sat_03_guilin_z14.jpg')}
        plateMeta={CHENGRUILONG_PLATES.cheng_sat_03_guilin_z14}
        startFocusLonLat={CHENGRUILONG_LANDMARKS.guilinHideoutRearWindow}
        endFocusLonLat={CHENGRUILONG_LANDMARKS.guilinKarstRidgeEscape}
        startZoom={1.16}
        endZoom={1.82}
        startPitch={24}
        endPitch={52}
        startBearing={18}
        endBearing={-14}
        flyStartFrame={t1}
        flyEndFrame={t3}
        showOpticalLoupe={true}
        loupeZoom={4}
        satLoupe={{
          targetLon: CHENGRUILONG_LANDMARKS.guilinKarstRidgeEscape[0],
          targetLat: CHENGRUILONG_LANDMARKS.guilinKarstRidgeEscape[1],
          screenX: 1620,
          screenY: 224,
          diameter: 232,
          zoomFactor: 4,
          progress: p12(f, t2 + 4, 18),
          loupePlateSrc: loupeAsset('cheng_sat_03_loupe.jpg'),
          loupePlateMeta: CHENGRUILONG_PLATES.cheng_sat_03_guilin_z14,
          labelTitle: '광시 구이린 산악 은신처 4X',
          labelSub: '포산 총격 직후 광시성 잠입 거점',
        }}
        polygons={[
          {
            id: 'poly-15',
            coordinates: CHENGRUILONG_GEO_ROUTES.guilinRidgePolygon,
            fillColor: 'rgba(239, 68, 68, 0.18)',
            strokeColor: '#EF4444',
            enterFrame: t1,
          },
        ]}
        routes={[
          {
            id: 'route-15',
            coordinates: CHENGRUILONG_GEO_ROUTES.guilinMountainEscapeRoute,
            color: '#F59E0B',
            widthPx: 6,
            drawStartFrame: t1,
            drawEndFrame: t3,
          },
        ]}
        pins={[
          {
            id: 'pin-15-1',
            lonLat: CHENGRUILONG_LANDMARKS.guilinHideoutRearWindow,
            label: '광시 구이린 은신·범행 거점',
            sublabel: '성(省) 경계 돌파 후 무장 강도 재개',
            appearFrame: t1,
            color: '#EF4444',
            dx: -170,
            dy: -86,
            align: 'right',
          },
          {
            id: 'pin-15-2',
            lonLat: CHENGRUILONG_LANDMARKS.guilinKarstRidgeEscape,
            label: '구이린 외곽 산악 탈출로',
            sublabel: '경찰 포위망 우회 산길 루트',
            appearFrame: t2,
            color: '#38BDF8',
            dx: 120,
            dy: 80,
            align: 'left',
          },
        ]}
        headerBadge="1998~1999 · 광시좡족자치구 구이린 3D 산악 위성도"
        headerTitle="포산 경찰 살해 후 광시 구이린으로 잠입한 산악 도주 경로"
      />
    </AbsoluteFill>
  );
};

// VOX_16 (B051-V01): "광시 구이린에서도 경찰이 은신처를 포위하자 총격전을 벌이며 지붕을 타고 탈출했습니다."
export const VoxScene16: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb ROOFTOP_SHOOTOUT_ESCAPE
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
          photoSrc={plateAsset('plate_16.jpg')}
          photoCaption="구이린 은신처 지붕 탈출"
          photoTag="1999.01 · 총격전 돌파"
          loupeFocusX={0.62}
          loupeFocusY={0.32}
          loupeLabel="은신처 후면 창문·지붕 탈출로"
          cutoutSrc={propAsset('prop_28_rooftop_window.png')}
          cutoutCaption="후면 창문 지붕 도주 흔적"
          cutoutBadge="총격 탈출"
          clippingHeadline="구이린 은신처 포위망 지붕 돌파"
          clippingBody="경찰 포위 직후 총격전 끝 지붕 능선 도주"
          stampText="ESCAPED"
        />
      </World>
    </Desk>
  );
};

// VOX_17 (B054-V01): "그의 현상금은 눈덩이처럼 불어났고 공안 당국은 그를 최우선 검거 대상으로 지정했습니다."
export const VoxScene17: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb BOUNTY_ESCALATION_PEAK
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
          photoSrc={plateAsset('plate_17.jpg')}
          photoCaption="최우선 검거 대상 지정"
          photoTag="PRIORITY #1 · 현상금 폭증"
          cutoutSrc={propAsset('prop_13_pried_safe_door.png')}
          cutoutCaption="연쇄 금고 강탈 사건 물증"
          cutoutBadge="특급 현상수배"
          clippingSource="WARRANT FILE:"
          clippingDate="2000.06 MINISTRY"
          clippingHeadline="현상금 최고액 경신 · 1순위 표적"
          clippingBody="전국 공안청 합동 최우선 검거 명령 하달"
          highlightText="최우선 검거 표적"
          stampText="WANTED"
          layoutVariant="left_hero"
        />
      </World>
    </Desk>
  );
};

// VOX_18 (B057-V01): "신분증 검사를 피하기 위해 그는 여객 열차 대신 화물 열차와 장거리 트럭만 골라 타며 이동했습니다."
export const VoxScene18: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb FREIGHT_YARD_BYPASS_PATH
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
          mainPhotoSrc={plateAsset('plate_18.jpg')}
          mainCaption="화물 열차·트럭 우회 기동"
          mainTag="FREIGHT BYPASS · 검문 회피"
          secondCaption="여객역 실명 검문 완전 우회"
          cutoutSrc={propAsset('prop_09_freight_truck_tarpaulin.png')}
          cutoutCaption="장거리 화물 트럭 은폐 천막"
          cutoutBadge="무검문 이동"
          clippingSource="TRANSIT LOG"
          clippingDate="2000-2004 ROUTE"
          clippingHeadline="화물 열차·장거리 트럭 잠입 이동"
          stampText="TRANSIT"
          variant="pinboard_web"
        />
      </World>
    </Desk>
  );
};

// VOX_19 (B060-V01): "추적을 원천 차단하기 위해 가족은 물론 고향의 그 누구와도 단 한 번의 연락조차 하지 않았습니다."
export const VoxScene19: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb ZERO_CONTACT_SEVERANCE
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
  const mainPlate = plateAsset('plate_19.jpg');

  return (
    <Desk>
      <World cam={cam}>
        <PaperUnfoldCollage
          f={f}
          t1={t1}
          t2={t2}
          t3={t3}
          dossierTitle="연고지 통신·송금 감청 기록부"
          dossierCode="13 YEARS · 연락 0건"
          leftPhotoSrc={mainPlate}
          leftCaption="고향 가족 통신망 감시"
          centerPhotoSrc={mainPlate}
          centerCaption="13년간 송금·통화 기록 전무"
          rightCutoutSrc={propAsset('prop_10_remittance_slip_zero.png')}
          rightCutoutCaption="우편 송금 내역 0건 조회서"
          rightHeadline="ARCHIVAL ENTRY · 연고 완전 단절"
          rightBody="가족 및 고향 지인 접촉 13년간 완전 차단"
          dimensionLabel="통화·송금 0건"
          stampText="ZERO TRACE"
        />
      </World>
    </Desk>
  );
};

// VOX_20 (B062-V01): "광둥과 광시 그리고 후난을 시작으로 저장과 충칭 안후이와 구이저우 장쑤와 푸젠 장시까지 무려 열 개 성을 넘나들었습니다."
export const VoxScene20: React.FC<VoxBeatSceneProps> = ({beat}) => {
  // @voxVerb SATELLITE_TEN_PROVINCE_CORRIDOR
  const f = useCurrentFrame();
  const dur = Math.max(90, beat.durationInFrames || 150);
  const [rawT1, rawT2, rawT3] = beat.triggers ?? [16, 64, 104];
  const t1 = Math.max(6, Math.min(rawT1, Math.round(dur * 0.25)));
  const t2 = Math.max(t1 + 16, Math.min(rawT2, Math.round(dur * 0.45)));
  const t3 = Math.max(t2 + 16, Math.min(rawT3, Math.round(dur * 0.65)));

  return (
    <AbsoluteFill style={{backgroundColor: '#0A0D12'}}>
      <GeoJson3DMapStage
        plateSrc={plateAsset('cheng_sat_05_10prov_z6.jpg')}
        plateMeta={CHENGRUILONG_PLATES.cheng_sat_05_10prov_z6}
        startFocusLonLat={CHENGRUILONG_LANDMARKS.foshanOrigin1996}
        endFocusLonLat={CHENGRUILONG_LANDMARKS.ganzhouCapture2009}
        startZoom={1.12}
        endZoom={1.68}
        startPitch={16}
        endPitch={44}
        startBearing={-12}
        endBearing={16}
        flyStartFrame={t1}
        flyEndFrame={t3}
        showOpticalLoupe={true}
        loupeZoom={4}
        satLoupe={{
          targetLon: CHENGRUILONG_LANDMARKS.ganzhouCapture2009[0],
          targetLat: CHENGRUILONG_LANDMARKS.ganzhouCapture2009[1],
          screenX: 1612,
          screenY: 230,
          diameter: 228,
          zoomFactor: 4,
          progress: p12(f, t2 + 4, 18),
          loupePlateSrc: loupeAsset('cheng_sat_05_loupe.jpg'),
          loupePlateMeta: CHENGRUILONG_PLATES.cheng_sat_05_10prov_z6,
          labelTitle: '10개 성 도주 종착지 간저우 4X',
          labelSub: '광역 철도·화물선 우회 도주망',
        }}
        polygons={[
          {
            id: 'poly-20',
            coordinates: CHENGRUILONG_GEO_ROUTES.tenProvinceSearchPolygon,
            fillColor: 'rgba(239, 68, 68, 0.18)',
            strokeColor: '#EF4444',
            enterFrame: t1,
          },
        ]}
        routes={[
          {
            id: 'route-20',
            coordinates: CHENGRUILONG_GEO_ROUTES.tenProvinceFugitiveOdysseyRoute,
            color: '#EF4444',
            widthPx: 6,
            drawStartFrame: t1,
            drawEndFrame: t3,
          },
        ]}
        pins={[
          {
            id: 'pin-20-1',
            lonLat: CHENGRUILONG_LANDMARKS.foshanOrigin1996,
            label: '광둥 · 광시 · 후난 초기 축선',
            sublabel: '남부 3개 성 연쇄 무장 범행지',
            appearFrame: t1,
            color: '#F59E0B',
            dx: -174,
            dy: -85,
            align: 'right',
          },
          {
            id: 'pin-20-2',
            lonLat: CHENGRUILONG_LANDMARKS.ganzhouCapture2009,
            label: '저장·충칭·안후이·장시 등 10개 성',
            sublabel: '총 13년간 광역 기동 도주 종착점',
            appearFrame: t2,
            color: '#EF4444',
            dx: 114,
            dy: 84,
            align: 'left',
          },
        ]}
        headerBadge="1996~2005 · 중국 남부·중부 10개 성(省) 광역 도주망"
        headerTitle="광둥·광시·후난·저장·충칭·안후이·구이저우·장쑤·푸젠·장시 10개 성 도주 지도"
      />
    </AbsoluteFill>
  );
};
