# ���񂾂���Bot �Z�b�g�A�b�v�ƃe�X�g�菇

## �����������
- �C���^�[�l�b�g�ڑ��A�p�\�R���ADiscord�A�J�E���g�AReplit�A�J�E���g�B

## �Z�b�g�A�b�v�菇
1. **Replit�A�J�E���g���쐬**:
   - [https://replit.com](https://replit.com) �ɃA�N�Z�X���A�����o�^�B
2. **Replit�v���W�F�N�g���쐬**:
   - �_�b�V���{�[�h�Łu+ New Repl�v���N���b�N�B
   - ������uPython�v�ɐݒ肵�A���O���uzunda-bot�v�Ɠ��́B
3. **�R�[�h��ǉ�**:
   - `main.py`��`zunda_bot.py`�̓��e���R�s�[���y�[�X�g�B
4. **�ˑ����C�u�������C���X�g�[��**:
   - �V�F���ňȉ������s�F`pip install discord.py openrouter transformers tiktoken bitsandbytes`
5. **���ϐ���ݒ�**:
   - Replit�́uSecrets�v�^�u�ňȉ���ݒ�F
     - `TOKEN`: Discord Bot�g�[�N���B
     - `CHANNEL_ID`: ����`�����l��ID�i�����j�B
     - `DEEPSEEK_API_KEY`: DeepSeek API�L�[�B
6. **�R�[�h�����s**:
   - Replit�́uRun�v�{�^�����N���b�N�B

## �e�X�g�菇
- **�ʏ�g�p�i1�b�ҋ@�j**:
  - `!zunda start`�ŋN����A�u���񂾂���v�ƃ`���b�g�ɏ����Ď���i��: �u���񂾂���A���C�H�v�j�B
  - �ʏ��1�b�ȓ��ɓ��k�قŉ������Ԃ�͂��B�������y���ɓ��삷�邩�m�F�B
- **�����Ȏg�p�i30�b�ҋ@�j**:
  - 1�b�ȓ���5��ȏ�܂���1���ȓ���5��ȏ㎿��𑗂�A���[�g�������������邩�m�F�B
  - �u���񂾂���A������Ƒ��Z������������̂��c1���҂��Ăق����̂���I�v�Ƃ������b�Z�[�W���\������A30�b�ҋ@�㉞�����Ԃ邩�m�F�B
- **�ʒm�I�v�V����**:
  - `!zunda notify off`�Œʒm���I�t�ɂ��A�ʒm���b�Z�[�W���\������Ȃ����m�F�B
  - `!zunda notify on`�Œʒm���I���ɖ߂��A�ʏ�̒ʒm���������邩�m�F�B
- **�G���[���O�m�F**:
  - �Ӑ}�I�ɃG���[�𔭐��i��: API�L�[�̖������j���A`error_logs.txt`�Ƀ^�C���X�^���v�t���ŃG���[���L�^����Ă��邩�m�F�B
- **�g�[�N�������m�F**:
  - �g�[�N���g�p�ʁi7,500�g�[�N��/���j�𒴂���܂Ŏ�����J��Ԃ��A�u���񂾂���A�����͈�����撣��������K���ɓ�����̂��c�v�Ƃ������b�Z�[�W���\������AMixtral 8x7B�Ōy�ʉ������Ԃ邩�m�F�B
  - 24���ԑҋ@��A�ʏ��DeepSeek R1�������������邩�m�F�B

## ���ӓ_
- Replit�̖����g�iCPU�A512MB RAM�j�œ��삷�邽�߁A���ׂ������ꍇ�������x������\������B
- Discord�̃��[�g�����i50���N�G�X�g/�b�A10,000���N�G�X�g/10���j�ɒ��ӂ��A�R�[�h��`safe_send()`�őΉ��B
- API�L�[��g�[�N���͈��S�ɊǗ��iReplit Secrets����ϐ����g�p�j�B

## �g���u���V���[�e�B���O
- **�G���[: 404 Not Found**:
  - Discord�`�����l��ID��Bot�g�[�N�������������m�F�BReplit��Secrets���Ċm�F�B
- **�G���[: 429 Too Many Requests**:
  - ���[�g�������������Ă��邽�߁A1���ҋ@��Ď��s�B�R�[�h��`safe_send()`�Ŏ����Ή��ς݁B
- **�G���[: API�L�[������**:
  - DeepSeek API�L�[�����������m�F�BReplit Secrets���X�V�B

## ���C�Z���X
MIT���C�Z���X�i�ύX�\�j�B