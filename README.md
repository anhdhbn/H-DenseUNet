# H-DenseUNet: Hybrid Densely Connected UNet for Liver and Tumor Segmentation from CT Volumes, TMI 2018. 
by [Xiaomeng Li](https://scholar.google.com/citations?user=uVTzPpoAAAAJ&hl=en), [Hao Chen](http://appsrv.cse.cuhk.edu.hk/~hchen/), [Xiaojuan Qi](https://xjqi.github.io/), [Qi Dou](http://appsrv.cse.cuhk.edu.hk/~qdou/), [Chi-Wing Fu](http://www.cse.cuhk.edu.hk/~cwfu/), [Pheng-Ann Heng](http://www.cse.cuhk.edu.hk/~pheng/). 


### Sử dụng 2 models.
Vũ Thành Đạt sử dụng Resnet-50 ở lớp decoder (model 1)
Duong Hong Anh giảm số filter của model cũ rồi train lại (model 2)

Kết quả thu được: cả 2 models đều có số param khoảng 9M tuy nhiên model 2 cho kết quả tốt hơn

Sau khi giảm số filter xuống một nửa và train trên 10 file .nii đầu tiên với 2 epoch và validate trên 2 file bất kì thì kết quả thu được loss trên tập train là ..., loss trên tập val ...

