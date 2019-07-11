# H-DenseUNet: Hybrid Densely Connected UNet for Liver and Tumor Segmentation from CT Volumes, TMI 2018. 
by [Xiaomeng Li](https://scholar.google.com/citations?user=uVTzPpoAAAAJ&hl=en), [Hao Chen](http://appsrv.cse.cuhk.edu.hk/~hchen/), [Xiaojuan Qi](https://xjqi.github.io/), [Qi Dou](http://appsrv.cse.cuhk.edu.hk/~qdou/), [Chi-Wing Fu](http://www.cse.cuhk.edu.hk/~cwfu/), [Pheng-Ann Heng](http://www.cse.cuhk.edu.hk/~pheng/). 


### Sử dụng 2 models.
- __Vũ Thành Đạt__ sử dụng Resnet-50 ở lớp decoder (__model 1__)
- __Duong Hong Anh__ giảm số filter của model cũ rồi train lại (__model 2__)

Kết quả thu được: cả 2 models đều có số param khoảng 9M tuy nhiên __model 2__ cho kết quả tốt hơn

Sau khi giảm số filter xuống một nửa và train trên __10__ file .nii đầu tiên với __2__ epoch và validate trên __2__ file bất kì thì kết quả thu được loss trên tập train là 0.5129 __acc__: 0.9188, loss trên tập val 0.3454 __acc__: 0.8962

