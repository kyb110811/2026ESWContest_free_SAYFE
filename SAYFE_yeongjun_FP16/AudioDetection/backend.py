"""Use the official FrameMN and prediction wrapper, without importing training code."""
import hashlib
from contextlib import redirect_stdout
import io
import math
import sys
from pathlib import Path

from .settings import ROOT, UPSTREAM_COMMIT


class PretrainedSED:
    def __init__(self, config):
        # Only the audio entry point imports this backend. Vision dependencies
        # and sys.path are unaffected when running the existing main.py.
        sys.path.insert(0,str(ROOT/'.deps'))
        sys.path.insert(0,str(ROOT/'vendor'/'PretrainedSED'))
        import torch
        from data_util.audioset_classes import as_strong_train_classes
        from models.frame_mn.Frame_MN_wrapper import FrameMNWrapper
        from models.prediction_wrapper import PredictionsWrapper

        self.torch, self.device = torch, config['device']
        if self.device == 'cuda' and not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable; set device=cpu explicitly to use CPU')
        torch.set_num_threads(config['cpu_threads'])
        checkpoint = ROOT/'resources'/(config['model_name']+'_strong_1.pt')
        if not checkpoint.is_file():
            raise FileNotFoundError(f'{checkpoint}: run ./setup.sh first')
        weights = torch.load(checkpoint,map_location='cpu',weights_only=True)
        trained_labels = list(as_strong_train_classes)
        if weights['strong_head.bias'].shape[0] != len(trained_labels):
            raise ValueError('Checkpoint class count does not match AudioSet Strong labels')
        # Keep model output indices aligned while excluding Mechanisms
        # from all published inference results.
        self.output_indices = [i for i, label in enumerate(trained_labels) if label != 'Mechanisms']
        self.labels = [trained_labels[i] for i in self.output_indices]
        with redirect_stdout(io.StringIO()):
            base = FrameMNWrapper(.6 if config['model_name']=='frame_mn06' else 1.)
        self.model = PredictionsWrapper(base,embed_dim=weights['strong_head.weight'].shape[1])
        self.model.load_state_dict(weights,strict=True)
        self.model.eval().to(self.device)
        self.tail_frames = math.ceil(config['decision_seconds']/config['window_seconds']*self.model.seq_len)
        self.metadata = dict(model_name=config['model_name'],device=self.device,class_count=len(self.labels),
                             model_class_count=len(trained_labels),excluded_labels=['Mechanisms'],
                             checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                             upstream_commit=UPSTREAM_COMMIT,sample_rate=config['sample_rate'],
                             window_seconds=config['window_seconds'],decision_seconds=config['decision_seconds'])

    def predict(self, waveforms):
        """All class probabilities over only the newest decision interval.

        Official strong logits are [batch, class, 250 time frames]. Taking max
        across the latest frames retains brief explosions, without keeping an
        event active just because it occurred earlier in the 10-second context.
        """
        torch = self.torch
        with torch.inference_mode():
            waveforms = torch.as_tensor(waveforms,dtype=torch.float32,device=self.device)
            strong,_ = self.model(self.model.mel_forward(waveforms))
            scores = strong[:,self.output_indices,-self.tail_frames:].float().sigmoid().amax(dim=-1)
        return scores.cpu().numpy()
